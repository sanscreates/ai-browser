#!/bin/bash
# Fetch Chromium's DEPS-managed dependencies for an AI Browser checkout.
#
# Layout: gclient wants a root directory holding `.gclient` and a solution
# directory literally named `src` (Chromium's DEPS hard-codes `src/...` paths),
# and it refuses to follow symlinks. So the repo itself must live at
# $ROOT/src (we use ~/aib-build/src; any other path can symlink *to* it).
# The solution is *unmanaged*: gclient never touches our git branch, it only
# fetches third-party deps into it and runs hooks.
#
# Usage: aib/scripts/fetch_deps.sh [--nohooks] [--hooks-only]
# Env:   AIB_MIN_FREE_GB  (default 15) abort if free disk drops below this.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
ROOT="$(dirname "$REPO")"
MIN_FREE_GB="${AIB_MIN_FREE_GB:-15}"
export PATH="$HOME/depot_tools:$PATH"
# We never want depot_tools to phone home with usage metrics.
export DEPOT_TOOLS_METRICS=0
export DEPOT_TOOLS_UPDATE=0

free_gb() { df -g "$HOME" | awk 'NR==2 {print $4}'; }

if [[ "$(basename "$REPO")" != "src" ]]; then
  echo "The repo must be checked out in a directory named 'src' (is: $REPO)" >&2
  exit 1
fi
if [[ ! -f "$ROOT/.gclient" ]]; then
  cat > "$ROOT/.gclient" <<'EOF'
solutions = [
  {
    "name": "src",
    "url": "https://github.com/sanscreates/ai-browser.git",
    "managed": False,
    "custom_deps": {},
    "custom_vars": {
      "checkout_configuration": "small",
      "checkout_pgo_profiles": True,
      "checkout_js_coverage_modules": False,
      "checkout_android": False,
      "checkout_ios": False,
      "checkout_fuchsia": False,
      "checkout_src_internal": False,
      "checkout_telemetry_dependencies": False,
      "generate_location_tags": False,
    },
  },
]
target_os = ["mac"]
target_os_only = True
EOF
fi

echo "free disk: $(free_gb) GB (minimum $MIN_FREE_GB GB)"
if (( $(free_gb) < MIN_FREE_GB + 30 )); then
  echo "Refusing to start: a sync needs ~30 GB headroom above the floor." >&2
  exit 1
fi

# Disk watchdog: kill the sync if we approach the floor.
watchdog() {
  while sleep 20; do
    if (( $(free_gb) < MIN_FREE_GB )); then
      echo "DISK FLOOR REACHED ($(free_gb) GB free); aborting sync" >&2
      pkill -f "gclient.py sync" || true
      pkill -f "gclient.py runhooks" || true
      return
    fi
  done
}
watchdog &
WD=$!
trap 'kill $WD 2>/dev/null || true' EXIT

cd "$ROOT"
if [[ "${1:-}" != "--hooks-only" ]]; then
  gclient sync --nohooks --no-history --shallow -j 8
fi
if [[ "${1:-}" != "--nohooks" ]]; then
  gclient runhooks
fi
# Not in DEPS: the built-in content blocker's pinned uBlock Origin release.
python3 "$REPO/aib/scripts/fetch_ublock.py"
echo "done; free disk: $(free_gb) GB"
