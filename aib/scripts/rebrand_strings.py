#!/usr/bin/env python3
# Copyright 2026 The AI Browser Authors. BSD-3-Clause (same as Chromium).
"""Reversibly rebrand UI strings from "Chromium" to "AI Browser".

The branded strings live in chromium_strings.grd (plus its .grdp parts) and
components_chromium_strings.grd. Translations in .xtb files are keyed by a
fingerprint of the English source text, so changing the English text
orphans them. This script:
  1. replaces the product name in the .grd/.grdp message text;
  2. asks grit for every message's old and new translation ID;
  3. rewrites the .xtb files with the new IDs and the product name
     replaced in each translation.
"The Chromium Authors" (copyright) and "Chromium OS" are left alone.

Like scrub_domains.py it runs at build time (aib/scripts/build.sh), caches
originals outside the repo and refuses to overwrite files edited since.

Usage: rebrand_strings.py apply|revert|status
"""

import hashlib
import json
import os
import re
import shutil
import sys

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'grit'))
from grit import grd_reader  # noqa: E402
from grit.node import message as grit_message  # noqa: E402

CACHE = os.path.join(os.path.dirname(REPO), 'aib-rebrand-cache')
GRDS = ['chrome/app/chromium_strings.grd',
        'components/components_chromium_strings.grd']
NAME_RE = re.compile(r'\bChromium\b(?!\s+(?:Authors|OS)\b)(?!OS\b)')
NEW_NAME = 'AI Browser'


def rebrand(text):
  return NAME_RE.sub(NEW_NAME, text)


def message_ids(grd):
  root = grd_reader.Parse(os.path.join(REPO, grd), skip_validation_checks=True)
  ids = {}
  for node in root.Preorder():
    if isinstance(node, grit_message.MessageNode):
      ids[node.attrs['name']] = node.GetCliques()[0].GetId()
  return ids


def parts_and_xtbs(grd):
  base = os.path.dirname(grd)
  text = open(os.path.join(REPO, grd), encoding='utf-8').read()
  parts = [os.path.normpath(os.path.join(base, p))
           for p in re.findall(r'<part\s+file="([^"]+)"', text)]
  xtbs = [os.path.normpath(os.path.join(base, p))
          for p in re.findall(r'<file\s+path="([^"]+\.xtb)"', text)]
  return parts, xtbs


def sha(path):
  with open(os.path.join(REPO, path), 'rb') as f:
    return hashlib.sha256(f.read()).hexdigest()


def load_manifest():
  try:
    with open(os.path.join(CACHE, 'manifest.json'), encoding='utf-8') as f:
      return json.load(f)
  except FileNotFoundError:
    return {'files': {}}


def save_manifest(m):
  os.makedirs(CACHE, exist_ok=True)
  with open(os.path.join(CACHE, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(m, f, indent=1, sort_keys=True)


def backup_and_write(m, rel, new_text):
  path = os.path.join(REPO, rel)
  with open(path, encoding='utf-8') as f:
    old_text = f.read()
  if new_text == old_text:
    return
  dst = os.path.join(CACHE, 'files', rel)
  os.makedirs(os.path.dirname(dst), exist_ok=True)
  shutil.copyfile(path, dst)
  with open(path, 'w', encoding='utf-8') as f:
    f.write(new_text)
  m['files'][rel] = {'rebranded': sha(rel)}


def cmd_apply():
  m = load_manifest()
  if m['files']:
    sys.exit('already rebranded; run revert first')
  changed_ids = 0
  try:
    for grd in GRDS:
      parts, xtbs = parts_and_xtbs(grd)
      old_ids = message_ids(grd)
      for rel in [grd] + parts:
        with open(os.path.join(REPO, rel), encoding='utf-8') as f:
          backup_and_write(m, rel, rebrand(f.read()))
      new_ids = message_ids(grd)
      remap = {old_ids[n]: new_ids[n] for n in old_ids
               if n in new_ids and old_ids[n] != new_ids[n]}
      changed_ids += len(remap)

      def fix(match):
        tid = remap.get(match.group(2), match.group(2))
        return f'{match.group(1)}{tid}{match.group(3)}{rebrand(match.group(4))}'

      for rel in xtbs:
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
          continue
        with open(path, encoding='utf-8') as f:
          text = f.read()
        text = re.sub(r'(<translation id=")(\d+)(">)(.*?)(?=</translation>)',
                      fix, text, flags=re.S)
        backup_and_write(m, rel, text)
  finally:
    save_manifest(m)
  print(f'rebranded {len(m["files"])} files; {changed_ids} translation ids '
        'remapped')


def cmd_revert():
  m = load_manifest()
  conflicts = []
  for rel, info in sorted(m['files'].items()):
    if sha(rel) != info['rebranded']:
      conflicts.append(rel)
      continue
    shutil.copyfile(os.path.join(CACHE, 'files', rel), os.path.join(REPO, rel))
    os.remove(os.path.join(CACHE, 'files', rel))
  m['files'] = {k: v for k, v in m['files'].items() if k in conflicts}
  save_manifest(m)
  for c in conflicts:
    print('CONFLICT (edited after rebrand, left alone):', c)
  print(f'reverted; {len(conflicts)} conflicts')
  return 1 if conflicts else 0


def main():
  cmd = sys.argv[1] if len(sys.argv) > 1 else ''
  if cmd == 'apply':
    return cmd_apply()
  if cmd == 'revert':
    return cmd_revert()
  if cmd == 'status':
    n = len(load_manifest()['files'])
    print('rebranded' if n else 'clean', f'({n} files)')
    return 0
  sys.exit(__doc__)


if __name__ == '__main__':
  sys.exit(main() or 0)
