#!/usr/bin/env python3
# Copyright 2026 The AI Browser Authors. BSD-3-Clause (same as Chromium).
"""Register an AI Browser base::Feature as a chrome://flags entry.

One call edits the four places Chromium needs for a flag:
  chrome/browser/about_flags.cc       entry (+ variations) and the include
  chrome/browser/flag_descriptions.h  name/description strings
  chrome/browser/flag-metadata.json   owners/expiry, kept alphabetical
  tools/metrics/histograms/enums.xml  LoginCustomFlags hashes
                                      (AboutFlagsHistogramTest)

Usage: register_flag.py [--root DIR] SPEC.json   (object or list of objects)
       --root edits copies of the four files under DIR instead of the repo
       (aib/scripts/commit_flag.sh uses this to commit only our changes).
Spec keys:
  name         internal flag name, e.g. "aib-popups-to-tabs"
  id           C++ stem for the description constants, e.g. "AibPopupsToTabs"
  visible      visible name
  description  one-sentence description
  os           FeatureEntry OS mask, e.g. "kOsDesktop" (default kOsAll)
  feature      C++ feature, e.g. "aib::features::kAibPopupsToTabs"
  feature_name BASE_FEATURE string name, e.g. "AibPopupsToTabs"
  include      header declaring the feature
  variations   optional [{"label": "Always", "params": {"mode": "always"}}]
"""

import json
import os
import re
import sys

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'metrics', 'common'))
import codegen_shared  # noqa: E402  (Chromium's flag-hash helper)

FILES = {
    'about': 'chrome/browser/about_flags.cc',
    'desc': 'chrome/browser/flag_descriptions.h',
    'meta': 'chrome/browser/flag-metadata.json',
    'enums': 'tools/metrics/histograms/enums.xml',
}
ABOUT = DESC = META = ENUMS = None


def set_root(root):
  """Points the four registration files at `root` (default: the repo)."""
  global ABOUT, DESC, META, ENUMS
  ABOUT, DESC, META, ENUMS = (os.path.join(root, FILES[k])
                              for k in ('about', 'desc', 'meta', 'enums'))
OWNERS = '//components/aib/OWNERS'
EXPIRY = 200  # Our flags are long-lived product options.

VAR_MARK = '// AI Browser flag variations.\n'
ENTRY_MARK = '    // Add new entries above this line.\n'


def read(p):
  with open(p, encoding='utf-8') as f:
    return f.read()


def write(p, s):
  with open(p, 'w', encoding='utf-8') as f:
    f.write(s)


def cstr(s):
  return json.dumps(s)


def wrap_string(prefix, text, indent='    '):
  """Formats `prefix = "text";` within 80 columns."""
  one = f'{prefix} {cstr(text)};'
  if len(one) <= 80:
    return one + '\n'
  words, lines, cur = text.split(' '), [], ''
  width = 80 - len(indent) - 2
  for w in words:
    cand = (cur + ' ' + w) if cur else w
    if len(cand) + 1 > width and cur:
      lines.append(cur + ' ')
      cur = w
    else:
      cur = cand
  lines.append(cur)
  body = '\n'.join(indent + cstr(l) for l in lines)
  return f'{prefix}\n{body};\n'


INC_MARK = '// AI Browser feature headers.\n'


def add_include(s, header):
  """Adds `header` to our own include block (created on first use, right
  before the first conditional include section)."""
  inc = f'#include "{header}"\n'
  if inc in s:
    return s
  if INC_MARK not in s:
    first = s.index('\n#include "components/')
    cond = s.index('\n#if ', first)
    s = s[:cond + 1] + INC_MARK + '\n' + s[cond + 1:]
  start = s.index(INC_MARK) + len(INC_MARK)
  end = s.index('\n\n', start - 1) + 1
  block = sorted(set(s[start:end].splitlines(keepends=True)) | {inc})
  return s[:start] + ''.join(block) + s[end:]


def register(spec):
  sid, name = spec['id'], spec['name']
  feature, fname = spec['feature'], spec['feature_name']
  os_mask = spec.get('os', 'kOsAll')

  # flag_descriptions.h
  d = read(DESC)
  if f'k{sid}Name[]' not in d:
    block = ('\n// AI Browser.\n' +
             wrap_string(f'inline constexpr char k{sid}Name[] =',
                         spec['visible']) +
             wrap_string(f'inline constexpr char k{sid}Description[] =',
                         spec['description']))
    end = '\n}  // namespace flag_descriptions\n'
    d = d.replace(end, block + end, 1)
    write(DESC, d)

  # about_flags.cc
  a = read(ABOUT)
  if f'{{"{name}",' not in a:
    a = add_include(a, spec['include'])
    value = f'FEATURE_VALUE_TYPE({feature})'
    if spec.get('variations'):
      if VAR_MARK not in a:
        anchor = '// When adding a new choice, add it to the end of the list.\n'
        a = a.replace(anchor, VAR_MARK + '\n' + anchor, 1)
      arrs = []
      vars_ = []
      for i, v in enumerate(spec['variations']):
        pname = f'k{sid}Params{i}'
        params = ', '.join(f'{{{cstr(k)}, {cstr(val)}}}'
                           for k, val in v['params'].items())
        arrs.append(f'const FeatureEntry::FeatureParam {pname}[] = {{\n'
                    f'    {params}}};\n')
        vars_.append(f'    {{{cstr(" - " + v["label"])}, {pname}, nullptr}},\n')
      code = (''.join(arrs) +
              f'const FeatureEntry::FeatureVariation k{sid}Variations[] = {{\n'
              + ''.join(vars_) + '};\n')
      a = a.replace(VAR_MARK, VAR_MARK + code, 1)
      value = (f'FEATURE_WITH_PARAMS_VALUE_TYPE({feature},\n'
               f'                                    k{sid}Variations,\n'
               f'                                    {cstr(fname)})')
    entry = (f'    {{{cstr(name)},\n'
             f'     flag_descriptions::k{sid}Name,\n'
             f'     flag_descriptions::k{sid}Description,\n'
             f'     {os_mask},\n'
             f'     {value}}},\n\n')
    a = a.replace(ENTRY_MARK, entry + ENTRY_MARK, 1)
    write(ABOUT, a)

  # flag-metadata.json (alphabetical by name)
  m = read(META)
  if f'"name": "{name}"' not in m:
    names = re.findall(r'^  \{\n    "name": "([^"]+)"', m, re.M)
    after = next((n for n in names if n > name), None)
    block = (f'  {{\n    "name": "{name}",\n'
             f'    "owners": [ "{OWNERS}" ],\n'
             f'    "expiry_milestone": {EXPIRY}\n  }},\n')
    if after:
      anchor = f'  {{\n    "name": "{after}"'
      m = m.replace(anchor, block + anchor, 1)
    else:
      m = m.rstrip().rstrip(']').rstrip() + ',\n' + block.rstrip(',\n') + '\n]\n'
    write(META, m)

  # enums.xml LoginCustomFlags: insert each new entry at its sorted
  # position (the enum is ordered by value), leaving everything else as is.
  e = read(ENUMS)
  start = e.index('<enum name="LoginCustomFlags">')
  end = e.index('</enum>', start)
  for suffix in ('disabled', 'enabled'):
    label = f'{fname}:{suffix}'
    if f'label="{label}"' in e[start:end]:
      continue
    # Same value generate_flag_enums.py computes: low 32 bits, signed.
    v = codegen_shared.HashName(label) & 0xffffffff
    v = v - (1 << 32) if v >= (1 << 31) else v
    line = f'  <int value="{v}" label="{label}"/>\n'
    pos = None
    for m in re.finditer(r'^  <int value="(-?\d+)" label="[^"]+"/>\n',
                         e[start:end], re.M):
      if int(m.group(1)) > v:
        pos = start + m.start()
        break
    if pos is None:
      pos = end
    e = e[:pos] + line + e[pos:]
    end = e.index('</enum>', start)
  write(ENUMS, e)
  print(f'registered {name}')


def main():
  args = sys.argv[1:]
  root = REPO
  if args and args[0] == '--root':
    root, args = args[1], args[2:]
  set_root(root)
  spec = json.loads(read(args[0]))
  for s in spec if isinstance(spec, list) else [spec]:
    register(s)


if __name__ == '__main__':
  main()
