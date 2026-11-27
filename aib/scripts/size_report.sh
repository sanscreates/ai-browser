#!/bin/bash
# Size breakdown of a built .app bundle.
#
# Usage: aib/scripts/size_report.sh [path/to/App.app] [--compare other.app]
#        [--append "label"]   (appends a table row to aib/BENCHMARKS.md)
# Default app: out/aib/AI Browser.app
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
APP="${REPO}/out/aib/AI Browser.app"
COMPARE=""
LABEL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --compare) COMPARE="$2"; shift 2 ;;
    --append) LABEL="$2"; shift 2 ;;
    *) APP="$1"; shift ;;
  esac
done

bytes() { du -sk "$1" 2>/dev/null | awk '{print $1 * 1024}'; }
mb() { awk -v b="$1" 'BEGIN { printf "%.1f", b / 1048576 }'; }

report() {
  local app="$1"
  [[ -d "$app" ]] || { echo "no such app: $app" >&2; return 1; }
  local fw
  fw="$(find "$app/Contents/Frameworks" -maxdepth 1 -name '*.framework' | head -1)"
  local fwname fwbin
  fwname="$(basename "$fw" .framework)"
  fwbin="$(find "$fw/Versions" -maxdepth 2 -type f -name "$fwname" | head -1)"
  local res
  res="$(find "$fw/Versions" -maxdepth 2 -type d -name Resources | head -1)"
  local total fwb paks locales nloc helpers
  total=$(bytes "$app")
  fwb=$(stat -f %z "$fwbin")
  paks=$(find "$res" -maxdepth 1 -name '*.pak' -exec stat -f %z {} + |
         awk '{s += $1} END {print s + 0}')
  locales=$(find "$res" -maxdepth 2 -path '*.lproj/*.pak' -exec stat -f %z {} + |
            awk '{s += $1} END {print s + 0}')
  nloc=$(find "$res" -maxdepth 1 -type d -name '*.lproj' | wc -l | tr -d ' ')
  helpers=$(bytes "$fw/Versions/Current/Helpers" || echo 0)
  echo "app=$app"
  echo "total_mb=$(mb "$total")"
  echo "framework_binary_mb=$(mb "$fwb")"
  echo "paks_mb=$(mb "$paks")"
  echo "locale_paks_mb=$(mb "$locales") (${nloc} locales)"
  echo "helpers_mb=$(mb "$helpers")"
  echo "--- largest files in Resources:"
  find "$res" -maxdepth 1 -type f -exec stat -f '%z%t%N' {} + | sort -rn |
    head -8 | awk -F'\t' '{n = split($2, p, "/");
                            printf "  %8.1f MB  %s\n", $1 / 1048576, p[n]}'
  REPORT_ROW="| $(date +%Y-%m-%d) | ${LABEL} | $(mb "$total") | $(mb "$fwb") | $(mb "$paks") | $(mb "$locales") (${nloc}) |"
}

report "$APP"
ROW="$REPORT_ROW"
if [[ -n "$COMPARE" ]]; then
  echo
  report "$COMPARE"
fi
if [[ -n "$LABEL" ]]; then
  echo "$ROW" >> "$REPO/aib/BENCHMARKS.md"
  echo "appended to aib/BENCHMARKS.md: $ROW"
fi
