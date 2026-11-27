#!/usr/bin/env python3
# Copyright 2026 The AI Browser Authors. BSD-3-Clause (same as Chromium).
"""Reversibly rewrite Google-family hostnames in source to a dead TLD.

Any hostname that ends in a domain listed in aib/domains/domains.txt gets
the suffix `.aib-invalid` appended, e.g.

    https://clients2.google.com/cr/report
 -> https://clients2.google.com.aib-invalid/cr/report

An ASCII TLD containing a hyphen can never be delegated, so the result
can't resolve anywhere. The browser also refuses to resolve or fetch
`*.aib-invalid` hosts (net::IsAibScrubbedHost() in net/base/url_util.h), so nothing
reaches DNS either. Appending, rather than replacing, keeps every
literal consistent: URL constants, host-equality checks and suffix
matches like ".google.com" are all rewritten the same way.

Sub-commands:
  survey    Count matched registrable domains in candidate files (helps
            curate domains.txt).
  generate  Write aib/domains/files.list: every candidate file with a match.
  apply     Scrub the files in files.list. Originals are cached outside the
            repo (default: <gclient root>/aib-scrub-cache) with a manifest.
  revert    Restore originals from the cache. Refuses to touch a file that
            changed since it was scrubbed, unless --force.
  status    Show whether the tree is scrubbed.

`apply --only FILE...` and `revert --only FILE...` act on just those files
(paths relative to the repo), so one scrubbed file can be edited and
committed without restoring, and then rebuilding, the whole tree.

Scrubbing happens only at build time. Never commit scrubbed source:
`revert` before rebasing or committing.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor

SUFFIX = '.aib-invalid'
REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
DOMAINS_FILE = os.path.join(REPO, 'aib', 'domains', 'domains.txt')
FILES_LIST = os.path.join(REPO, 'aib', 'domains', 'files.list')
DEFAULT_CACHE = os.path.join(os.path.dirname(REPO), 'aib-scrub-cache')

# Text formats that end up compiled into, or packaged with, the browser.
INCLUDE_EXT = {
    '.c', '.cc', '.cpp', '.h', '.hpp', '.m', '.mm', '.inc', '.def',
    '.js', '.mjs', '.ts', '.html', '.css', '.json', '.json5',
    '.grd', '.grdp', '.xtb', '.idl', '.mojom', '.proto', '.xml', '.plist',
    '.rs', '.svg', '.txt', '.xslt',
}
# Directory names (any depth) whose contents are never scrubbed.
EXCLUDE_DIR_NAMES = {
    '.git', 'test', 'tests', 'testing', 'test_data', 'testdata',
    'test_support', 'web_tests', 'layout_tests', 'docs', 'doc', 'samples',
    'examples', 'example', 'fuzzers', 'fuzz', 'benchmarks', 'perf_tests',
    'node_modules', '__pycache__', 'unittests', 'e2e', 'e2e_non_hosted',
    'chromedriver', 'infra',
}
# Top-level-relative path prefixes never scrubbed: toolchains, build
# machinery (it downloads from Google at build time by design), tests,
# platforms we don't build, and our own files.
EXCLUDE_PREFIXES = (
    'aib/', 'out', 'build/', 'buildtools/', 'tools/', 'testing/',
    'android_webview/', 'ios/', 'fuchsia_web/', 'chromecast/',
    'chromeos/', 'ash/', 'chrome/android/', 'chrome/test/',
    'content/test/', 'content/shell/', 'headless/', 'infra/', 'agents/',
    'native_client_sdk/', 'remoting/', 'third_party/llvm-build',
    'third_party/rust-toolchain', 'third_party/rust-src',
    'third_party/depot_tools', 'third_party/node', 'third_party/ninja',
    'third_party/cpython3', 'third_party/libc++/src/test',
    'third_party/siso', 'third_party/catapult', 'third_party/android_',
    'third_party/jdk', 'third_party/r8', 'third_party/kotlin',
    'third_party/blink/web_tests', 'third_party/blink/perf_tests',
    'third_party/devtools-frontend/src/test',
    'third_party/devtools-frontend/src/scripts',
    'third_party/wpt_tools', 'third_party/chromium-variations',
    'third_party/search_engines_data/resources/definitions/',
    # Validated against an origin allowlist by bake_in_configs.py at build
    # time; dead data anyway, since Domain Reliability is never enabled.
    'components/domain_reliability/baked_in_configs/',
)
# Exact files we deliberately keep: security data, not network endpoints.
EXCLUDE_FILES = {
    # HSTS/pinning preload list: keeping Google entries is protective, and
    # the generator rejects unknown TLDs.
    'net/http/transport_security_state_static.json',
    'net/http/transport_security_state_static_pins.json',
    # Public Suffix List and lookalike-domain tables are security inputs.
    'net/base/registry_controlled_domains/effective_tld_names.dat',
    # Certificate Transparency log list (its URLs are not contacted by us
    # at runtime; CT log list updates come via component updater, which we
    # disable).
    'components/certificate_transparency/data/log_list.json',
}
EXCLUDE_NAME_RE = re.compile(
    r'(_|-|\.)(unit|browser|interactive_ui|api|perf|ui|integration)?tests?\b'
    r'|_test_util|_test_utils|_testing\.|test_utils?\.|_fuzzer|_mock\.|mock_|'
    r'fake_|_fake\.|\.test\.|\.spec\.|^OWNERS$|^DEPS$|README|CHANGELOG|LICENSE',
    re.IGNORECASE)
MAX_BYTES = 16 * 1024 * 1024

# Entries written as `name.*` in domains.txt expand to every TLD in
# Chromium's own list of Google TLDs, plus a few generic ones.
GOOGLE_TLD_LIST_H = os.path.join(REPO, 'components', 'google', 'core',
                                 'common', 'google_tld_list.h')
EXTRA_TLDS = ['com', 'net', 'org']


def wildcard_tld():
  with open(GOOGLE_TLD_LIST_H, encoding='utf-8') as f:
    body = f.read().split('#define GOOGLE_TLD_LIST', 1)[1]
  body = body.split('\n\n', 1)[0]
  tlds = set(re.findall(r'"([a-z.]+)"', body)) | set(EXTRA_TLDS)
  if len(tlds) < 100:
    sys.exit(f'could not parse Google TLD list from {GOOGLE_TLD_LIST_H}')
  return '(?:' + '|'.join(
      re.escape(t) for t in sorted(tlds, key=len, reverse=True)) + ')'


WILDCARD_TLD = wildcard_tld()

# A hostname is only rewritten in literal/URL context: preceded by a quote,
# '/', '@', '*', '=', ':', '\\', '%', '>', the start of a line, or a '.' that
# itself follows a non-identifier character (".google.com"). This
# keeps JS property chains like `window.google.sn` (sn is a Google ccTLD!)
# untouched, while catching "https://x.google.com", ".google.com",
# "*.google.com", url=www.google.com, <host>google.com</host>, etc.
_CONTEXT = (r'(?:(?<=["\'`/@*=:\\%>])|(?<=[^A-Za-z0-9_\-]\.)|(?<=^\.)|^)')


def load_domains(path=DOMAINS_FILE):
  """Returns the domain entries; `!host` lines are exact-host exclusions."""
  domains = []
  with open(path, encoding='utf-8') as f:
    for line in f:
      line = line.split('#', 1)[0].strip()
      if line:
        domains.append(line.lower())
  if not [d for d in domains if not d.startswith('!')]:
    sys.exit(f'no domains in {path}')
  return domains


def excluded_hosts(domains):
  return {d[1:] for d in domains if d.startswith('!')}


def make_sub(domains):
  """Returns a function that scrubs a text, honoring exclusions."""
  regex = build_regex(domains)
  skip = excluded_hosts(domains)

  def repl(m):
    host = m.group(1)
    return host if host.lower() in skip else host + SUFFIX

  return lambda text: regex.sub(repl, text)


def build_regex(domains):
  alts = []
  for d in sorted({d for d in domains if not d.startswith('!')}, key=len,
                  reverse=True):
    if d.endswith('.*'):
      alts.append(re.escape(d[:-2]) + r'\.' + WILDCARD_TLD)
    else:
      alts.append(re.escape(d))
  # A hostname: optional subdomain labels, then a listed domain. It must not
  # be glued to a preceding identifier character, and must not continue
  # into another label (so `google.com.evil` and `google.community` are not
  # touched). `(?!-invalid)` keeps the scrub idempotent.
  return re.compile(
      _CONTEXT +
      r'((?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)*'
      r'(?:' + '|'.join(alts) + r'))'
      r'(?![A-Za-z0-9_\-])(?!\.[A-Za-z0-9])(?!' + re.escape(SUFFIX) + r')',
      re.IGNORECASE | re.MULTILINE)


def is_candidate(rel):
  if rel in EXCLUDE_FILES or rel.startswith(EXCLUDE_PREFIXES):
    return False
  parts = rel.split('/')
  if any(p in EXCLUDE_DIR_NAMES for p in parts[:-1]):
    return False
  name = parts[-1]
  if os.path.splitext(name)[1].lower() not in INCLUDE_EXT:
    return False
  if EXCLUDE_NAME_RE.search(name):
    return False
  return True


def iter_candidates(root):
  for dirpath, dirnames, filenames in os.walk(root):
    rel_dir = os.path.relpath(dirpath, root)
    rel_dir = '' if rel_dir == '.' else rel_dir.replace(os.sep, '/') + '/'
    # Prune excluded directories early.
    keep = []
    for d in dirnames:
      rel = rel_dir + d + '/'
      if d in EXCLUDE_DIR_NAMES or rel.startswith(EXCLUDE_PREFIXES):
        continue
      if os.path.islink(os.path.join(dirpath, d)):
        continue
      keep.append(d)
    dirnames[:] = keep
    for f in filenames:
      rel = rel_dir + f
      if is_candidate(rel):
        yield rel


def read_text(path):
  try:
    if os.path.getsize(path) > MAX_BYTES or os.path.islink(path):
      return None
    with open(path, 'rb') as f:
      data = f.read()
  except OSError:
    return None
  if b'\0' in data[:8192]:
    return None
  try:
    return data.decode('utf-8')
  except UnicodeDecodeError:
    return None


_REGEX = None
_SKIP = set()


def _init_worker(domains):
  global _REGEX, _SKIP
  _REGEX = build_regex(domains)
  _SKIP = excluded_hosts(domains)


def _scan_one(rel):
  path = os.path.join(REPO, rel)
  # Read-only files belong to CIPD-managed toolchain packages: never ours to
  # rewrite.
  if not os.access(path, os.W_OK):
    return rel, []
  text = read_text(path)
  if text is None:
    return rel, []
  hosts = (m.group(1).lower() for m in _REGEX.finditer(text))
  return rel, [h for h in hosts if h not in _SKIP]


def scan(domains, files, jobs):
  with ProcessPoolExecutor(jobs, initializer=_init_worker,
                           initargs=(domains,)) as ex:
    yield from ex.map(_scan_one, files, chunksize=256)


def registrable(host, domains_re):
  # Shorten a matched host to the listed domain that matched, for survey.
  labels = host.split('.')
  for i in range(len(labels)):
    cand = '.'.join(labels[i:])
    if domains_re.fullmatch(cand):
      return cand
  return host


def cmd_survey(args):
  domains = load_domains()
  dre = re.compile(r'(?:' + '|'.join(
                       (re.escape(d[:-2]) + r'\.' + WILDCARD_TLD)
                       if d.endswith('.*') else re.escape(d)
                       for d in domains if not d.startswith('!')) + r')',
                   re.IGNORECASE)
  counts, hosts = {}, {}
  files = list(iter_candidates(REPO))
  for rel, found in scan(domains, files, args.jobs):
    for h in found:
      r = registrable(h, dre)
      counts[r] = counts.get(r, 0) + 1
      hosts.setdefault(r, {}).setdefault(h, 0)
      hosts[r][h] += 1
  for r, n in sorted(counts.items(), key=lambda kv: -kv[1]):
    top = sorted(hosts[r].items(), key=lambda kv: -kv[1])[:args.top]
    print(f'{n:7d} {r:30s} ' + ', '.join(f'{h}({c})' for h, c in top))


def cmd_generate(args):
  domains = load_domains()
  files = sorted(iter_candidates(REPO))
  hits = sorted(rel for rel, found in scan(domains, files, args.jobs) if found)
  with open(FILES_LIST, 'w', encoding='utf-8') as f:
    f.write('# Generated by aib/scripts/scrub_domains.py generate. '
            'Do not edit by hand.\n')
    for rel in hits:
      f.write(rel + '\n')
  print(f'{len(hits)} files (of {len(files)} candidates) -> {FILES_LIST}')


def load_files_list():
  with open(FILES_LIST, encoding='utf-8') as f:
    return [l.strip() for l in f if l.strip() and not l.startswith('#')]


def sha(data):
  return hashlib.sha256(data).hexdigest()


def manifest_path(cache):
  return os.path.join(cache, 'manifest.json')


def load_manifest(cache):
  try:
    with open(manifest_path(cache), encoding='utf-8') as f:
      return json.load(f)
  except FileNotFoundError:
    return {'files': {}}


def save_manifest(cache, manifest):
  os.makedirs(cache, exist_ok=True)
  tmp = manifest_path(cache) + '.tmp'
  with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=1, sort_keys=True)
  os.replace(tmp, manifest_path(cache))


def cmd_apply(args):
  scrub = make_sub(load_domains())
  manifest = load_manifest(args.cache)
  only = set(args.only or [])
  if manifest['files'] and not args.force and not only:
    sys.exit('Tree already scrubbed (manifest has entries). Run revert first, '
             'or --force to scrub on top.')
  manifest['suffix'] = SUFFIX
  changed = missing = 0
  try:
    for rel in load_files_list():
      if only and (rel not in only or rel in manifest['files']):
        continue
      path = os.path.join(REPO, rel)
      text = read_text(path)
      if text is None:
        missing += 1
        continue
      new = scrub(text)
      if new == text:
        continue
      orig = text.encode('utf-8')
      out = new.encode('utf-8')
      backup = os.path.join(args.cache, 'files', rel)
      os.makedirs(os.path.dirname(backup), exist_ok=True)
      with open(backup, 'wb') as f:
        f.write(orig)
      shutil.copymode(path, backup)
      manifest['files'][rel] = {'orig': sha(orig), 'scrubbed': sha(out)}
      with open(path, 'wb') as f:
        f.write(out)
      changed += 1
  finally:
    # Always record what was changed, even if we stop partway.
    save_manifest(args.cache, manifest)
  print(f'scrubbed {changed} files; {missing} listed files missing/unreadable;'
        f' cache: {args.cache}')


def cmd_revert(args):
  manifest = load_manifest(args.cache)
  only = set(args.only or [])
  restored, conflicts, kept = 0, [], []
  for rel, info in sorted(manifest['files'].items()):
    if only and rel not in only:
      kept.append(rel)
      continue
    path = os.path.join(REPO, rel)
    backup = os.path.join(args.cache, 'files', rel)
    try:
      with open(path, 'rb') as f:
        cur = sha(f.read())
    except FileNotFoundError:
      cur = None
    if cur == info['orig']:
      pass  # Already original.
    elif cur != info['scrubbed'] and not args.force:
      conflicts.append(rel)
      continue
    else:
      shutil.copyfile(backup, path)
    os.remove(backup)
    restored += 1
  for rel in conflicts:
    print(f'CONFLICT (modified after scrub, left alone): {rel}')
  keep = set(conflicts) | set(kept)
  manifest['files'] = {k: v for k, v in manifest['files'].items() if k in keep}
  save_manifest(args.cache, manifest)
  print(f'restored {restored} files; {len(conflicts)} conflicts')
  return 1 if conflicts else 0


def cmd_status(args):
  manifest = load_manifest(args.cache)
  n = len(manifest['files'])
  print('scrubbed' if n else 'clean', f'({n} files in manifest)')


def main():
  p = argparse.ArgumentParser(description=__doc__,
                              formatter_class=argparse.RawTextHelpFormatter)
  p.add_argument('--cache', default=DEFAULT_CACHE)
  p.add_argument('-j', '--jobs', type=int, default=os.cpu_count())
  sub = p.add_subparsers(dest='cmd', required=True)
  s = sub.add_parser('survey')
  s.add_argument('--top', type=int, default=4)
  sub.add_parser('generate')
  a = sub.add_parser('apply')
  a.add_argument('--force', action='store_true')
  a.add_argument('--only', nargs='+', metavar='FILE')
  r = sub.add_parser('revert')
  r.add_argument('--force', action='store_true')
  r.add_argument('--only', nargs='+', metavar='FILE')
  sub.add_parser('status')
  args = p.parse_args()
  return {'survey': cmd_survey, 'generate': cmd_generate, 'apply': cmd_apply,
          'revert': cmd_revert, 'status': cmd_status}[args.cmd](args) or 0


if __name__ == '__main__':
  sys.exit(main())
