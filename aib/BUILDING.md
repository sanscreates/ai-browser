# Building AI Browser (macOS, Apple silicon)

Exact steps from a fresh Mac to a signed `AI Browser.app`. Chromium 160 (upstream commit position 1756194).

## Requirements
- Apple silicon Mac, macOS 15 or newer, 16 GB RAM minimum (24 GB+ recommended for the ThinLTO link).
- **Full Xcode** (the Command Line Tools are not enough), with the macOS SDK. Install it from the App Store. `aib/scripts/build.sh` auto-detects `xcode-select -p`, then `/Applications/Xcode.app`, then `~/Downloads/Xcode.app`, or honours `DEVELOPER_DIR`. Verified with Xcode 27.0 (27A266a, macOS 27.0 SDK).
- About **60 GB free disk**: source with deps ~20 GB, plus the official build output. The scripts refuse to run below a 15 GB floor (`AIB_MIN_FREE_GB`).
- Homebrew `git-lfs` (`brew install git-lfs`; one dependency, `third_party/litert/src`, uses LFS).
- Python 3 and git.

## 1. depot_tools
```sh
git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git ~/depot_tools
export PATH="$HOME/depot_tools:$PATH" DEPOT_TOOLS_METRICS=0
```

## 2. Source
gclient needs the solution directory to be named `src`, inside a root that holds `.gclient`:
```sh
mkdir -p ~/aib-build && cd ~/aib-build
git clone --depth 1 --branch aib https://github.com/sanscreates/ai-browser.git src
cd src
```
(For a full-history clone, drop `--depth 1`. The `aib` branch carries all our changes on top of upstream `main`.)

## 3. Dependencies
```sh
aib/scripts/fetch_deps.sh
```
This writes `~/aib-build/.gclient` (unmanaged solution, `checkout_configuration=small`, mac only, PGO profiles on) and runs `gclient sync --nohooks --no-history --shallow` followed by `gclient runhooks`. The hooks download the pinned clang/rust/gn/siso toolchains and the PGO profiles from Google storage; that is build-time only (DECISIONS D4).

## 4. Build
```sh
aib/scripts/build.sh --skip-fetch          # unsigned, ad-hoc-signed DMG
```
Pipeline: apply `aib/patches/deps/` → `prune_binaries.py apply` → `scrub_domains.py apply` → `gn gen out/aib` with `aib/args.gn` → `autoninja -C out/aib chrome` → `scrub_domains.py revert` (always, even on failure) → package to `out/aib/dist/`.

A clean official build (ThinLTO + PGO, ~78k steps) takes many hours on a 10-core M-series Mac. It's incremental afterwards.

### Signed and notarized
```sh
export AIB_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
xcrun notarytool store-credentials aib-notary --apple-id you@example.com --team-id TEAMID
export AIB_NOTARY_PROFILE=aib-notary
aib/scripts/build.sh --skip-fetch
```
This builds `chrome/installer/mac` and runs Chromium's `sign_chrome.py`, which signs the helpers and frameworks inside-out with the right entitlements and identifiers, then notarizes and staples.

## 5. Verify
```sh
aib/scripts/net_audit.sh                 # expect: unsolicited hosts: 0
aib/scripts/size_report.sh
aib/scripts/bench.sh --label "my build"  # vs the same-commit Chromium snapshot
```

## Working on the code
- Never commit while scrubbed: `aib/scripts/scrub_domains.py status` must say `clean`. `build.sh` reverts on exit unless `--keep-scrubbed` is used.
- Before rebasing onto a new Chromium: `scrub_domains.py revert`, `prune_binaries.py restore`, then `git rebase`, then regenerate the lists (`scrub_domains.py generate`, `prune_binaries.py generate --out out/aib`) and review the diffs.
- New chrome://flags entries: `aib/scripts/register_flag.py spec.json` writes all four registration files.
- Carry our changes to a fresh checkout: `aib/scripts/export_patches.sh`, then `git am aib/patches/*.patch`.
