# AI Browser: benchmarks

Measured results only. Produced by `aib/scripts/bench.sh` (speed and memory, against the stock Chromium snapshot built from the same upstream commit) and `aib/scripts/size_report.sh` (bundle size). Nothing in this file is estimated.

Method notes:
- Both browsers run with identical flags: fresh temporary profile, no first-run UI, background-timer and occlusion throttling off, 1400×1000 window. See `aib/scripts/bench/cdp_bench.mjs`.
- Memory is summed RSS of the browser's whole process tree. RSS over-counts shared pages, but the same method is used for both browsers.
- Benchmarks are refused while a build is running.

## Size

| Date | Change | .app total (MB) | Framework binary (MB) | .pak files (MB) | Locale paks (MB, count) |
|---|---|---|---|---|---|

## Speed and memory

_No AI Browser build has finished yet, so there are no measurements._
