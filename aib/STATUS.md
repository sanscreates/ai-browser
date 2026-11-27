# AI Browser: status

_Updated by Claude as work progresses. Read this first, then `git log main..aib --oneline`._

- Base: Chromium 160.0.8188.0 (upstream `main` @ 7d0cc1fc42, Cr-Commit-Position 1756194), shallow clone.
- ungoogled-chromium reference: 158.0.8127.88 (read-only clones at `~/Downloads/ungoogled-reference` and `~/Downloads/ungoogled-reference-macos`).
- Branch: `aib`, pushed to `origin/aib`. `main` mirrors upstream.
- Repo location: `~/aib-build/src`. `~/Downloads/AI browser` is a symlink to it (DECISIONS D1).

## Decisions waiting for the owner
- **Peter Lowe's ad server list** isn't bundled with the built-in blocker: its license forbids commercial use (DECISIONS D13). uBlock Origin downloads it on its own at the first list update. To bundle it anyway, see D13.

## Blockers
- **None hard.** Xcode isn't in /Applications, but `~/Downloads/Xcode.app` (Xcode 27.0, macOS 27 SDK) works through `DEVELOPER_DIR` (D2). Install Xcode properly from the App Store for a durable setup.
- **The full official build isn't finished yet** (see In progress). Everything marked "pending build" below depends on it.

## Working-tree state right now (important before committing or rebasing)
While the build runs, the tree is **pruned, scrubbed and rebranded**:
- `python3 aib/scripts/scrub_domains.py status` → scrubbed
- `python3 aib/scripts/rebrand_strings.py status` → rebranded
- `python3 aib/scripts/prune_binaries.py status` → pruned

Before committing anything in those files, or rebasing, run `rebrand_strings.py revert`, then `scrub_domains.py revert`, then (for a rebase) `prune_binaries.py restore`. `aib/scripts/build.sh` does the reverts automatically.

## Done
- **Phase 0, recon:** `aib/FEATURES.md` covers every ungoogled-chromium patch, flag, list and macOS change, with our status and commit hashes.
- **Tooling** (`aib/scripts/`):
  - `fetch_deps.sh`, `build.sh`, `export_patches.sh`
  - `fetch_ublock.py`: pinned, checksum-verified uBlock Origin release for the built-in blocker
  - `scrub_domains.py` + `aib/domains/`: verified exact apply/revert round trip; `--only FILE...` reverts or re-applies single files
  - `prune_binaries.py` + `aib/prune/files.list`: 691 prebuilt files, ~1.4 GB
  - `rebrand_strings.py`: verified translation coverage unchanged
  - `register_flag.py`
  - `net_audit.sh` + `netlog_hosts.py`
  - `bench.sh` + `bench/cdp_bench.mjs`
  - `size_report.sh`
  - Docs: `BUILDING.md`, `DECISIONS.md` (D1–D13), `THIRD_PARTY_NOTICES.md`, `BENCHMARKS.md` (no numbers yet).
- **Phase 1, de-Google and telemetry:** ~40 focused commits.
  - No telemetry: variations fetch, X-Client-Data, UMA/UKM/DWA and crash consent, crash upload, GCM, Domain Reliability, intranet redirect probes, network time, background component update checks, Google/AI/model component registrations, Optimization Guide, autofill crowdsourcing, affiliation lookups, WebRTC log upload, DevTools remote base, SCT auditing.
  - Gemini (Glic), actor, skills, Lens, compose and on-device models are off; the AI omnibox shortcuts are gone.
  - Sign-in, Safe Browsing and Translate are off by default (Translate needs a user-chosen server).
  - DuckDuckGo is the default engine; Google tracking params are dropped from search URLs; the NTP is always the local page.
  - Private default prefs (D8), FedCM off, no first-run import, CT enforced.
  - The network stack blocks `*.aib-invalid`.
- **Built-in ad and tracker blocker (D13):** uBlock Origin 1.77.4 (Manifest V2, full `webRequestBlocking`, the way Brave keeps MV2 blockers working) as a component extension that can't be removed or disabled. Its toolbar button is always pinned and shows what is blocked, with a per-site on/off switch; `chrome://flags/#aib-content-blocker` turns it off everywhere. It is denied Chromium's component-extension privileges. Filter lists are served brotli-compressed from a 2.9 MB pak; with its 6.9 MB of files that's about 10 MB instead of 28 MB unpacked.
- **Phase 2, flags:** 42 `aib-*` chrome://flags entries (41 options plus the blocker switch).
  - Fingerprinting noise (canvas, measureText, client rects) is on by default. The Battery API always reports a fixed status.
  - Options: WebGL info spoofing, reduced system info, no UA client hints, referrer trimming, popups to tabs, keep window with last tab, keep old history, scroll tabs, avatar button, CRX install handling, clear data on exit, and more.
  - Expired flags stay usable; MV2 extensions keep working.
  - All flags have metadata, descriptions and enums entries (checked by script: alphabetical, none missing).
- **Phase 3, speed:** official, ThinLTO, PGO (official profile fetched), symbol_level 0, stripping, apple-m1 CPU baseline (D11). Startup work removed: incident-reporting delayed analysis, Google/AI component registrations, periodic DIAL discovery, the GCM start.
- **Phase 4, size:** locale keep-list (23 locales, no gendered variants: 23 `.lproj` vs 216 upstream per `gn gen`); compose and the on-device model service compiled out; RLZ, remoting, Hangouts and updater off.
- **Phase 5, branding:** "AI Browser" app/framework/helper names, bundle id `com.sanscreates.aibrowser`, `aibrowser://` scheme, local-network usage description, placeholder icon, build-time UI-string rebrand.
- **Verification so far:**
  - `gn gen` succeeds with `aib/args.gn` (and with a product name containing a space).
  - The `//base` smoke build succeeds.
  - gn check and checkdeps pass for all agent-written Phase 2 code.
  - Built-in blocker: `gn gen`, `gn check` and checkdeps pass. Every changed source compiles without warnings (component loader, allowlist, resource manager, extension management, context menu, extensions menu item, action view model, permissions_data, simple_feature, about_flags). The brotli pak builds (13 resources, 2.9 MB).
  - Net-audit harness smoke-tested on stock Google Chrome 158: 15 unsolicited hosts in 30 s (`aib/net_audit/baseline-google-chrome.md`).

## In progress
- Full `chrome` build in `out/aib`, scrubbed and rebranded (log `~/aib-build/build8.log`; driver `~/aib-build/tmp/run_build.sh -k 0`). Build 7 was interrupted at 12.5k of 47k steps with no failures. Build 8 includes the built-in blocker and started with 33k steps left. It's the first compile of all Phase 1–2 code, so compile fixes may follow.
- Net audit of the stock Chromium 160.0.8188.0 snapshot (same commit) as a baseline.

## Pending (needs the finished build)
- Built-in blocker at runtime: it loads, the button is pinned and can't be unpinned or removed, the popup works, ads are blocked, Incognito works, the flag turns it off, and uBlock Origin finds its pak-served lists (first-run log in its dashboard).
- `aib/scripts/net_audit.sh` on AI Browser (target: zero unsolicited hosts).
- `aib/scripts/bench.sh` against the same-commit stock snapshot (already downloaded to `~/aib-build/stock-chromium/1756194`).
- `aib/scripts/size_report.sh`, and per-change size deltas in BENCHMARKS.md (including the blocker's real `.app` cost).
- `bench.sh` with the blocker on (the shipped default) and with `aib-content-blocker` disabled, to measure its per-request cost.
- `aib/scripts/export_patches.sh` milestone export.
- Signed or notarized packaging needs a Developer ID (not available on this machine); `build.sh` produces an ad-hoc-signed DMG.
