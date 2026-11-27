#!/bin/bash
# Regenerate aib/patches/ from the aib branch, so our changes can be carried
# to a fresh Chromium checkout with `git am aib/patches/*.patch`.
# Refuses to run while the tree is scrubbed.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
cd "$REPO"
if [[ "$(python3 aib/scripts/scrub_domains.py status)" != clean* ]] ||
   [[ "$(python3 aib/scripts/rebrand_strings.py status)" != clean* ]]; then
  echo "tree is scrubbed or rebranded; revert both first" >&2
  exit 1
fi
rm -f aib/patches/[0-9]*.patch
git format-patch --quiet --no-signature main..aib -o aib/patches/
ls aib/patches/*.patch | wc -l | xargs echo "patches:"
