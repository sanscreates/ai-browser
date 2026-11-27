#!/usr/bin/env python3
# Copyright 2026 The AI Browser Authors. BSD-3-Clause (same as Chromium).
"""Fetch the uBlock Origin release that AI Browser ships as its built-in
ad and tracker blocker.

Downloads uBlock0_<VERSION>.chromium.zip from uBlock Origin's GitHub
releases, checks it against the pinned SHA-256 and unpacks it into
third_party/aib_ublock/src/ (not checked in):

  src/extension/  the extension minus assets/. Copied as-is into the app
                  bundle (Contents/Frameworks/<framework>/Resources/aib_ublock).
                  _locales/ is trimmed to the UI locales the browser ships.
  src/assets/     the packaged filter lists (~20 MB of text). They are packed
                  brotli-compressed into a .pak by aib_ublock_resources.grd and
                  served to the extension from there.
  src/STAMP       what the tree was unpacked from; reruns are no-ops.

The zip is uBlock Origin's own unmodified release build. Bump VERSION and
SHA256 together; the script then checks that the grd still lists exactly
the release's asset files.

Usage: fetch_ublock.py [--force] [--keep-locales all|LOCALE,...]
  --keep-locales  Chromium locale names to keep (default: the aib_keep_locales
                  default in build/config/locales.gni). "all" keeps every
                  locale uBlock Origin ships.
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile

VERSION = '1.77.4'
SHA256 = 'fe5c6ed9c6edfaf0dce1cff875b2629f647be40b8ac571c1a5f8fece8d22e5c4'
URL = ('https://github.com/gorhill/uBlock/releases/download/'
       f'{VERSION}/uBlock0_{VERSION}.chromium.zip')
ZIP_ROOT = 'uBlock0.chromium/'

# Packaged lists we don't redistribute. Peter Lowe's list is under the
# "McRae General Public License", which forbids any use that makes anybody
# money (DECISIONS D13). uBlock Origin still subscribes to it and downloads it
# from pgl.yoyo.org at its first list update.
EXCLUDED_ASSETS = {
    'assets/thirdparties/pgl.yoyo.org/as/README.md',
    'assets/thirdparties/pgl.yoyo.org/as/serverlist',
}

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEST = os.path.join(REPO, 'third_party', 'aib_ublock')
SRC = os.path.join(DEST, 'src')
GRD = os.path.join(DEST, 'aib_ublock_resources.grd')
LOCALES_GNI = os.path.join(REPO, 'build', 'config', 'locales.gni')
DEFAULT_LOCALE = 'en'  # The manifest's default_locale; always kept.


def default_keep_locales():
  with open(LOCALES_GNI, encoding='utf-8') as f:
    m = re.search(r'aib_keep_locales\s*=\s*\[(.*?)\]', f.read(), re.S)
  if not m:
    sys.exit(f'aib_keep_locales not found in {LOCALES_GNI}')
  return re.findall(r'"([^"]+)"', m.group(1))


def ublock_locale_dirs(chromium_locales, available):
  """Maps Chromium locale names to the _locales/ dirs that serve them.

  Chromium looks up an extension's messages as xx_YY, then xx, then the
  default locale, so a kept xx_YY also keeps xx.
  """
  keep = {DEFAULT_LOCALE}
  for loc in chromium_locales:
    name = 'en' if loc == 'en-US' else loc.replace('-', '_')
    for candidate in (name, name.split('_')[0]):
      if candidate in available:
        keep.add(candidate)
  return keep


def download(dest_dir):
  path = os.path.join(dest_dir, f'uBlock0_{VERSION}.chromium.zip')
  print(f'downloading {URL}')
  with urllib.request.urlopen(URL, timeout=120) as r, open(path, 'wb') as f:
    shutil.copyfileobj(r, f)
  with open(path, 'rb') as f:
    digest = hashlib.sha256(f.read()).hexdigest()
  if digest != SHA256:
    sys.exit(f'checksum mismatch for {URL}:\n  got      {digest}\n'
             f'  expected {SHA256}')
  return path


def safe_members(zf):
  """Yields (member, relative path) for regular files under ZIP_ROOT."""
  for info in zf.infolist():
    name = info.filename
    if info.is_dir():
      continue
    if not name.startswith(ZIP_ROOT):
      sys.exit(f'unexpected file outside {ZIP_ROOT}: {name}')
    rel = name[len(ZIP_ROOT):]
    parts = rel.split('/')
    if not rel or rel.startswith('/') or '..' in parts or '\\' in rel:
      sys.exit(f'unsafe path in zip: {name}')
    # Reject symlinks (stored as S_IFLNK in the high bits of external_attr).
    if (info.external_attr >> 16) & 0o170000 == 0o120000:
      sys.exit(f'symlink in zip: {name}')
    yield info, rel


def grd_asset_files():
  with open(GRD, encoding='utf-8') as f:
    return set(re.findall(r'file="src/(assets/[^"]+)"', f.read()))


def unpack(zip_path, keep_locales, staging):
  ext_dir = os.path.join(staging, 'extension')
  assets_dir = os.path.join(staging, 'assets')
  with zipfile.ZipFile(zip_path) as zf:
    members = list(safe_members(zf))
    available = {rel.split('/')[1] for _, rel in members
                 if rel.startswith('_locales/')}
    locale_dirs = (available if keep_locales is None else
                   ublock_locale_dirs(keep_locales, available))
    assets, dropped = set(), set()
    for info, rel in members:
      if rel.startswith('_locales/'):
        loc = rel.split('/')[1]
        if loc not in locale_dirs:
          dropped.add(loc)
          continue
      if rel in EXCLUDED_ASSETS:
        continue
      if rel.startswith('assets/'):
        out = os.path.join(staging, rel)
        assets.add(rel)
      else:
        out = os.path.join(ext_dir, rel)
      os.makedirs(os.path.dirname(out), exist_ok=True)
      with zf.open(info) as src, open(out, 'wb') as dst:
        shutil.copyfileobj(src, dst)

  if not os.path.isfile(os.path.join(ext_dir, 'manifest.json')):
    sys.exit('the release has no manifest.json')

  # The browser's resource loader requires text resources to be UTF-8.
  for rel in sorted(assets):
    with open(os.path.join(staging, rel), 'rb') as f:
      try:
        f.read().decode('utf-8')
      except UnicodeDecodeError:
        sys.exit(f'{rel} is not UTF-8')

  expected = grd_asset_files()
  if assets != expected:
    lines = [f'  + {a}' for a in sorted(assets - expected)]
    lines += [f'  - {a}' for a in sorted(expected - assets)]
    sys.exit(f'assets in {VERSION} differ from {os.path.relpath(GRD, REPO)}; '
             'update the grd:\n' + '\n'.join(lines))
  if not os.path.isdir(assets_dir):
    sys.exit('the release has no assets/ directory')
  return sorted(locale_dirs), sorted(dropped)


def main():
  p = argparse.ArgumentParser(description=__doc__,
                              formatter_class=argparse.RawTextHelpFormatter)
  p.add_argument('--force', action='store_true',
                 help='re-download even if src/ is up to date')
  p.add_argument('--keep-locales',
                 help='"all", or comma-separated Chromium locale names')
  args = p.parse_args()

  if args.keep_locales == 'all':
    keep_locales = None
  elif args.keep_locales:
    keep_locales = [l.strip() for l in args.keep_locales.split(',') if l]
  else:
    keep_locales = default_keep_locales()
  locales_key = 'all' if keep_locales is None else ','.join(sorted(keep_locales))
  stamp = (f'{VERSION} {SHA256} locales={locales_key} '
           f'excluded={",".join(sorted(EXCLUDED_ASSETS))}\n')
  stamp_path = os.path.join(SRC, 'STAMP')

  if not args.force and os.path.isfile(stamp_path):
    with open(stamp_path, encoding='utf-8') as f:
      if f.read() == stamp:
        print(f'uBlock Origin {VERSION} is up to date in '
              f'{os.path.relpath(SRC, REPO)}')
        return 0

  # Downloads go into their own fresh directory; staging is a sibling of
  # src/ so the final swap is a same-filesystem rename.
  with tempfile.TemporaryDirectory(prefix='aib-ublock-dl-') as dl:
    zip_path = download(dl)
    staging = tempfile.mkdtemp(prefix='.src-staging-', dir=DEST)
    try:
      kept, dropped = unpack(zip_path, keep_locales, staging)
      with open(os.path.join(staging, 'STAMP'), 'w', encoding='utf-8') as f:
        f.write(stamp)
      if os.path.isdir(SRC):
        shutil.rmtree(SRC)
      os.rename(staging, SRC)
    except BaseException:
      shutil.rmtree(staging, ignore_errors=True)
      raise
  print(f'uBlock Origin {VERSION} -> {os.path.relpath(SRC, REPO)}; '
        f'{len(kept)} locales kept, {len(dropped)} dropped')
  return 0


if __name__ == '__main__':
  sys.exit(main())
