#!/bin/bash
# Network audit: does the browser contact anything the user didn't ask for?
#
# 1. Launch the app with a brand-new profile and --log-net-log.
# 2. Leave it idle (default 300 s) on its new tab page.
# 3. Open a few sites through the running instance, wait, quit cleanly.
# 4. List every host from the NetLog: all idle-phase traffic is unsolicited,
#    and so is browse-phase traffic with no top-frame site (browser-made)
#    that isn't one of the sites we opened.
#
# Usage: aib/scripts/net_audit.sh [path/to/App.app] [--idle SECONDS]
# Output: report on stdout and in out/net_audit/report.md; exit 1 if any
# unsolicited host was seen.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
APP="${REPO}/out/aib/AI Browser.app"
IDLE=300
SITES=(https://example.com/ https://en.wikipedia.org/wiki/Web_browser
       https://developer.mozilla.org/en-US/)
SITE_DOMAINS="example.com,wikipedia.org,wikimedia.org,mozilla.org,mozilla.net"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --idle) IDLE="$2"; shift 2 ;;
    *) APP="$1"; shift ;;
  esac
done

BIN="$APP/Contents/MacOS/$(defaults read "$APP/Contents/Info" CFBundleExecutable)"
WORK="$REPO/out/net_audit"
rm -rf "$WORK"
mkdir -p "$WORK"
PROFILE="$WORK/profile"
NETLOG="$WORK/netlog.json"

FLAGS=(--user-data-dir="$PROFILE" --log-net-log="$NETLOG"
       --net-log-capture-mode=Default --no-first-run
       --no-default-browser-check)

echo "launching $BIN (idle ${IDLE}s)"
"$BIN" "${FLAGS[@]}" > "$WORK/stdout.log" 2>&1 &
PID=$!
sleep "$IDLE"

PHASE_START=$(python3 -c 'import time; print(int(time.time() * 1000))')
echo "$PHASE_START" > "$WORK/phase_start.txt"
for url in "${SITES[@]}"; do
  # A second launch with the same profile hands the URL to the running
  # instance (process singleton) and exits.
  "$BIN" "${FLAGS[@]}" "$url" >> "$WORK/stdout.log" 2>&1 || true
  sleep 20
done
sleep 30

# SIGTERM is a graceful shutdown for Chromium (the NetLog is flushed). We
# signal our own PID rather than quitting by bundle id, so an instance the
# user has open is never touched.
kill -TERM "$PID" 2>/dev/null || true
for _ in $(seq 1 60); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
kill -9 "$PID" 2>/dev/null || true

set +e
python3 "$REPO/aib/scripts/netlog_hosts.py" "$NETLOG" \
  --phase-start "$PHASE_START" --sites "$SITE_DOMAINS" | tee "$WORK/report.md"
rc=${PIPESTATUS[0]}
echo "netlog: $NETLOG"
exit "$rc"
