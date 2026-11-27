# AI Browser: status

_Updated by Claude as work progresses. Read this first, then `git log main..aib --oneline`._

- Base: Chromium 160.0.8188.0 (upstream `main` @ 7d0cc1fc42), shallow clone.
- ungoogled-chromium reference: 158.0.8127.88 (read-only clones at `~/Downloads/ungoogled-reference` and `~/Downloads/ungoogled-reference-macos`).
- Branch: `aib` (all our work). `main` mirrors upstream.
- Repo location: `~/aib-build/src`. `~/Downloads/AI browser` is a symlink to it (DECISIONS D1).

## Blockers
- **None hard right now.** Xcode isn't installed in /Applications, but `~/Downloads/Xcode.app` (Xcode 27.0, macOS 27 SDK) works through `DEVELOPER_DIR` (D2). `//base` built with it. For a durable setup, install Xcode into /Applications from the App Store.
- **Build time:** an official ThinLTO+PGO build of `chrome` is ~78k steps. On this shared machine (user apps running, and our processes stuck at nice ≥5 because we can't renice without root) it runs at roughly 2k steps/hour, i.e. well over a day. In progress; see below.

## Done
- Tooling: depot_tools in `~/depot_tools`; `git-lfs` via Homebrew (D5); `aib/scripts/fetch_deps.sh` (unmanaged gclient root, mac-only shallow sync, disk watchdog). Deps synced; free disk afterwards ~77 GB.
- Phase 0 recon: `aib/FEATURES.md` covers every ungoogled-chromium patch, flag, list and macOS change, with our status and commit.
- Domain scrubbing: `aib/scripts/scrub_domains.py` + `aib/domains/` (D6). Verified: apply on 5,702 files, then revert, leaves the main repo and all dependency checkouts clean. The browser refuses to resolve or fetch `*.aib-invalid` (131773ec24).
- Build args: `aib/args.gn`, all checked by `gn gen` (37,414 targets). Build-level removals: compose, on-device model service, internal optimization guide, RLZ, reporting, mDNS/service discovery, remoting, Hangouts extension, updater, field-trial config, Google API keys (D7).
- Phase 1 code changes (35 commits, prefixes `telemetry:`/`privacy:`): variations fetch, X-Client-Data, UMA/UKM/crash consent, crash upload, GCM, Domain Reliability, intranet redirect detector, network time, DNS probe host, private default prefs, sign-in off, Safe Browsing reporting off and SB off by default, Translate, autofill crowdsourcing, affiliation lookups, background component updates, Google/AI component registrations, Optimization Guide, Glic/Gemini/actor/skills/Lens, DuckDuckGo default, search tracking params, local NTP, scrubbed-host blocking, MV2 kept, distiller fonts, WebRTC logs, F1 help, API-key infobar, Web Store update-URL fill-in, DIAL periodic discovery, DevTools remote base, first-run import, FedCM.
- Branding (part 1): app name "AI Browser", bundle id `com.sanscreates.aibrowser`, `aibrowser://` scheme, local-network usage description (d4374ba6cb).
- Toolchain smoke test: `autoninja -C out/aib base` succeeded (Xcode 27 SDK, stock clang).

## In progress
- Full `chrome` build in `out/aib` (log `~/aib-build/build3.log`, driver `~/aib-build/tmp/run_build.sh`). Not yet compile-verified: the Phase 1 edits and `enable_mdns=false`/`enable_service_discovery=false` (ungoogled needed a build fix for these; we'll patch if the compile fails).
- Phase 2 flags; scripts (prune, net_audit, bench, size_report, build); BUILDING.md.

## Pending (needs a finished build)
- `aib/scripts/net_audit.sh` run (target: zero unsolicited hosts).
- Benchmarks vs stock Chromium 160.0.8188.0 and size measurements.
- UI-string rebrand ("Chromium" → "AI Browser" in chromium_strings.grd and its .xtb translations, keeping translation IDs consistent). Placeholder icon.
