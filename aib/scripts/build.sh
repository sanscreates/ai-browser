#!/bin/bash
# Build AI Browser end to end:
#   fetch deps -> fetch the built-in content blocker -> apply dep patches
#   -> prune -> scrub -> rebrand strings -> gn gen -> autoninja
#   -> unrebrand + unscrub (always) -> package
#
# Usage: aib/scripts/build.sh [--skip-fetch] [--out out/aib] [--keep-scrubbed]
#                             [--no-package]
# Env:
#   DEVELOPER_DIR         full Xcode (auto-detected: xcode-select, then
#                         /Applications/Xcode.app, then ~/Downloads/Xcode.app)
#   AIB_SIGN_IDENTITY     Developer ID Application identity. If set, the app
#                         is signed with Chromium's sign_chrome.py; if not,
#                         you get an ad-hoc-signed DMG for local use.
#   AIB_NOTARY_PROFILE    notarytool keychain profile (with an identity)
#   AIB_MIN_FREE_GB       disk floor (default 15)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
OUT="out/aib"
FETCH=1
KEEP_SCRUBBED=0
PACKAGE=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-fetch) FETCH=0; shift ;;
    --out) OUT="$2"; shift 2 ;;
    --keep-scrubbed) KEEP_SCRUBBED=1; shift ;;
    --no-package) PACKAGE=0; shift ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
cd "$REPO"
export PATH="$HOME/depot_tools:$PATH" DEPOT_TOOLS_METRICS=0 DEPOT_TOOLS_UPDATE=0
MIN_FREE_GB="${AIB_MIN_FREE_GB:-15}"

# --- Xcode -------------------------------------------------------------------
if [[ -z "${DEVELOPER_DIR:-}" ]]; then
  if xcodebuild -version >/dev/null 2>&1; then
    :
  elif [[ -d /Applications/Xcode.app ]]; then
    export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
  elif [[ -d "$HOME/Downloads/Xcode.app" ]]; then
    export DEVELOPER_DIR="$HOME/Downloads/Xcode.app/Contents/Developer"
  else
    echo "Full Xcode is required (Command Line Tools are not enough)." >&2
    exit 1
  fi
fi
xcodebuild -version | head -1

free_gb() { df -g "$HOME" | awk 'NR==2 {print $4}'; }
echo "free disk: $(free_gb) GB"
if (( $(free_gb) < MIN_FREE_GB + 10 )); then
  echo "Not enough disk: need at least $((MIN_FREE_GB + 10)) GB free." >&2
  exit 1
fi

# --- 1. deps ---------------------------------------------------------------
if [[ $FETCH == 1 ]]; then
  aib/scripts/fetch_deps.sh
fi

# The built-in content blocker (a pinned uBlock Origin release); a no-op when
# it's already unpacked, so it also runs with --skip-fetch.
python3 aib/scripts/fetch_ublock.py

# --- 2. patches for DEPS-managed repos (aib/patches/deps/<repo path>/*.patch)
if [[ -d aib/patches/deps ]]; then
  find aib/patches/deps -name '*.patch' | sort | while read -r p; do
    rel="${p#aib/patches/deps/}"; dep="$(dirname "$rel")"
    if git -C "$dep" apply --check "$REPO/$p" 2>/dev/null; then
      git -C "$dep" apply "$REPO/$p" && echo "applied $p"
    else
      echo "skipped $p (already applied or doesn't apply)"
    fi
  done
fi

# --- 3. prune prebuilt binaries (stays applied; restore before rebasing) ----
python3 aib/scripts/prune_binaries.py apply

# --- 4. scrub Google endpoints for the build; always restore afterwards -----
SCRUB_STATE=$(python3 aib/scripts/scrub_domains.py status)
if [[ "$SCRUB_STATE" == clean* ]]; then
  python3 aib/scripts/scrub_domains.py apply
fi
# UI strings: "Chromium" -> "AI Browser" (after scrubbing; undone first).
if [[ "$(python3 aib/scripts/rebrand_strings.py status)" == clean* ]]; then
  python3 aib/scripts/rebrand_strings.py apply
fi
unscrub() {
  if [[ $KEEP_SCRUBBED == 0 ]]; then
    python3 "$REPO/aib/scripts/rebrand_strings.py" revert || true
    python3 "$REPO/aib/scripts/scrub_domains.py" revert || true
  fi
}
trap unscrub EXIT

# --- 5. gn gen ---------------------------------------------------------------
mkdir -p "$OUT"
if ! cmp -s aib/args.gn "$OUT/args.gn"; then
  cp aib/args.gn "$OUT/args.gn"
fi
buildtools/mac/gn gen "$OUT"

# --- 6. build (with a disk watchdog) ----------------------------------------
( while sleep 30; do
    if (( $(free_gb) < MIN_FREE_GB )); then
      echo "DISK FLOOR REACHED ($(free_gb) GB); stopping build" >&2
      pkill -INT -f "siso ninja" || true
      exit
    fi
  done ) &
WD=$!
autoninja -C "$OUT" chrome
kill "$WD" 2>/dev/null || true

# --- 7. unscrub happens in the EXIT trap; package ----------------------------
[[ $PACKAGE == 1 ]] || exit 0
APP="$OUT/AI Browser.app"
DIST="$OUT/dist"
rm -rf "$DIST"
mkdir -p "$DIST"
VERSION=$(awk -F= '{v[$1]=$2} END {print v["MAJOR"]"."v["MINOR"]"."v["BUILD"]"."v["PATCH"]}' chrome/VERSION)
if [[ -n "${AIB_SIGN_IDENTITY:-}" ]]; then
  autoninja -C "$OUT" chrome/installer/mac
  SIGN_ARGS=(--input "$OUT" --output "$DIST" --identity "$AIB_SIGN_IDENTITY")
  if [[ -n "${AIB_NOTARY_PROFILE:-}" ]]; then
    SIGN_ARGS+=(--notarize staple
                --notary-arg="--keychain-profile=$AIB_NOTARY_PROFILE")
  else
    SIGN_ARGS+=(--notarize none)
  fi
  python3 "$OUT/AI Browser Packaging/sign_chrome.py" "${SIGN_ARGS[@]}"
else
  cp -R "$APP" "$DIST/"
  codesign --force --deep --sign - "$DIST/AI Browser.app"
  hdiutil create -volname "AI Browser" -srcfolder "$DIST/AI Browser.app" \
    -ov -format UDZO "$DIST/AI-Browser-$VERSION-arm64-unsigned.dmg"
fi
aib/scripts/size_report.sh "$APP"
echo "done: $DIST"
