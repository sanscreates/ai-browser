#!/bin/bash
# Benchmark AI Browser against stock Chromium built from the SAME upstream
# commit (the official Chromium snapshot for our main's Cr-Commit-Position).
#
# Usage: aib/scripts/bench.sh [--tasks startup,memory,speedometer,jetstream,motionmark]
#                             [--app "out/aib/AI Browser.app"] [--label text]
#                             [--no-append]
# Results are printed as JSON and (unless --no-append) appended to
# aib/BENCHMARKS.md. Only measured numbers are recorded.
#
# Caveat recorded with every run: Chromium snapshots are built by Google's
# bots without PGO/official settings, while our build is official+PGO.
# That's the only same-version stock build that exists (Google ships
# Chrome, not Chromium).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
APP="$REPO/out/aib/AI Browser.app"
TASKS="startup,memory,speedometer,jetstream,motionmark"
LABEL=""
APPEND=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tasks) TASKS="$2"; shift 2 ;;
    --app) APP="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --no-append) APPEND=0; shift ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done

if pgrep -f "siso ninja|autoninja" >/dev/null; then
  echo "A build is running; benchmarks would be skewed. Stop it first." >&2
  exit 1
fi

NODE="$REPO/third_party/node/mac_arm64/node-darwin-arm64/bin/node"
POS=$(git -C "$REPO" log -1 --format=%B main |
      sed -n 's/.*refs\/heads\/main@{#\([0-9]*\)}.*/\1/p')
STOCK_DIR="$(dirname "$REPO")/stock-chromium/$POS"
STOCK_APP="$STOCK_DIR/chrome-mac/Chromium.app"
if [[ ! -d "$STOCK_APP" ]]; then
  echo "downloading stock Chromium snapshot Mac_Arm/$POS"
  mkdir -p "$STOCK_DIR"
  curl -fL -o "$STOCK_DIR/chrome-mac.zip" \
    "https://storage.googleapis.com/chromium-browser-snapshots/Mac_Arm/$POS/chrome-mac.zip"
  (cd "$STOCK_DIR" && unzip -q chrome-mac.zip && rm chrome-mac.zip)
fi

exe() { echo "$1/Contents/MacOS/$(defaults read "$1/Contents/Info" CFBundleExecutable)"; }

run() {
  "$NODE" "$REPO/aib/scripts/bench/cdp_bench.mjs" --binary "$(exe "$1")" \
    --tasks "$TASKS" | tail -1
}

echo "== stock Chromium @$POS"
STOCK_JSON=$(run "$STOCK_APP")
echo "$STOCK_JSON"
echo "== AI Browser ($APP)"
AIB_JSON=$(run "$APP")
echo "$AIB_JSON"

if [[ $APPEND == 1 ]]; then
  python3 - "$REPO/aib/BENCHMARKS.md" "$POS" "$LABEL" "$STOCK_JSON" "$AIB_JSON" <<'EOF'
import json, sys, datetime, platform, subprocess
path, pos, label, stock, aib = sys.argv[1:6]
stock, aib = json.loads(stock), json.loads(aib)
keys = [('startup_fresh_profile_ms', 'Startup, fresh profile (ms, lower is better)'),
        ('startup_warm_median_ms', 'Startup, warm median (ms, lower is better)'),
        ('memory_idle_1tab_mb', 'Memory, 1 idle tab (MB RSS, lower is better)'),
        ('memory_10tabs_mb', 'Memory, 10 tabs (MB RSS, lower is better)'),
        ('speedometer3', 'Speedometer 3.1 (higher is better)'),
        ('jetstream2', 'JetStream 2.2 (higher is better)'),
        ('motionmark', 'MotionMark 1.3.1 (higher is better)')]
cpu = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                     capture_output=True, text=True).stdout.strip()
lines = [f'\n### {datetime.date.today()} {label}'.rstrip(),
         f'Machine: {cpu}, macOS {platform.mac_ver()[0]}. Stock = Chromium '
         f'snapshot Mac_Arm/{pos} (same upstream commit; non-PGO bot build).',
         '', '| Metric | Stock Chromium | AI Browser |', '|---|---|---|']
for k, name in keys:
    if k in stock or k in aib:
        lines.append(f'| {name} | {stock.get(k, "n/a")} | {aib.get(k, "n/a")} |')
errs = {k: v for d in (stock, aib) for k, v in d.items() if k.endswith('_error')}
if errs:
    lines.append('')
    lines += [f'- error: {k}: {v}' for k, v in errs.items()]
with open(path, 'a') as f:
    f.write('\n'.join(lines) + '\n')
print(f'appended to {path}')
EOF
fi
