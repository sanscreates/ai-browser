# AI Browser: decisions log

Judgment calls made without the owner present, newest last. Each entry: what, why, how to undo.

## D1. Repo moved to `~/aib-build/src`; old path is a symlink
- **What:** `~/Downloads/AI browser` was renamed (same filesystem, instant) to `~/aib-build/src`, and `~/Downloads/AI browser` is now a symlink pointing at it. `~/aib-build/.gclient` is the gclient root.
- **Why:** gclient requires the solution directory to be literally `src` (Chromium's DEPS hard-codes `src/...` paths) and refuses to sync through a symlink (`Dependency path 'src' goes through a symlink`). The original path also contains a space, which many Chromium build scripts handle poorly.
- **Undo:** `rm "~/Downloads/AI browser" && mv ~/aib-build/src "~/Downloads/AI browser"` (deps would then need a different gclient root).

## D2. Xcode: use the existing `~/Downloads/Xcode.app` through `DEVELOPER_DIR`
- **What:** The brief says full Xcode isn't installed, and `xcode-select -p` does point at the Command Line Tools. But `~/Downloads/Xcode.app` (Xcode 27.0, build 27A266a, MacOSX27.0 SDK) is on disk and works. Our build scripts export `DEVELOPER_DIR=~/Downloads/Xcode.app/Contents/Developer` per process.
- **Why:** That installs nothing and changes no system state (`xcode-select -s` would need sudo). The brief only forbids *installing* Xcode.
- **Undo:** Install Xcode into /Applications and drop the `DEVELOPER_DIR` export (scripts honor an existing `DEVELOPER_DIR`).

## D3. gclient checkout configuration
- **What:** An unmanaged solution (gclient never touches our git branches), `checkout_configuration=small`, `target_os=["mac"]` only, `checkout_pgo_profiles=True`, and no android/ios/fuchsia/telemetry/js-coverage deps. `--no-history --shallow`. The disk watchdog kills the sync if free space falls below 15 GB.
- **Why:** The disk budget is ~87 GB. PGO profiles are needed for the speed goal (see D4).

## D4. Keep PGO on
- **What:** `chrome_pgo_phase=2` with the official profiles that `checkout_pgo_profiles` fetches. Unlike ungoogled-chromium (which sets `chrome_pgo_phase=0`), we keep it.
- **Why:** PGO is one of the largest single speed wins in Chromium. The profile is fetched from Google storage at **build time** only, and the shipped browser contacts nothing because of it. The brief explicitly accepts this.

## D5. Installed `git-lfs` with Homebrew
- **What:** `brew install git-lfs` (user-level, no sudo). We did not run `git lfs install` (it would edit ~/.gitconfig or the system config).
- **Why:** `third_party/litert/src` uses LFS, and its checkout fails without the binary (`git-lfs: command not found`).

## D6. Domain scrubbing design
- **Placeholder:** we *append* `.aib-invalid` to matched hostnames (`clients2.google.com` → `clients2.google.com.aib-invalid`) rather than replacing letters. A hyphenated ASCII TLD can never be delegated, and appending keeps host equality and suffix checks consistent everywhere. The browser also refuses to resolve `*.aib-invalid` (net patch), so scrubbed hosts never reach DNS.
- **Scope:** curated Google-family registrable domains (`aib/domains/domains.txt`). `google.*` expands to Chromium's own `google_tld_list.h`. Not scrubbed: `chromium.org`/`googlesource.com` (docs and build-time fetches), `android.com` (XML namespaces), `gmail.com`/`googlemail.com` (email domains in autofill data, not endpoints), and identifier hosts (`type.googleapis.com` for protobuf Any, `schemas.google.com`).
- **Context rule:** a hostname is only rewritten in literal/URL context (after a quote, `/`, `@`, `*`, `=`, `:`, `\`, `%`, `>`, line start, or a dot that follows a non-identifier character). Without it, JS like `window.google.sn` (`sn` is a Google ccTLD) would break.
- **Never scrubbed:** toolchains and build machinery (they download from Google at *build* time by design), tests, the HSTS preload JSON, the PSL, and read-only CIPD packages.
- **Trade-off:** "Learn more" and help links to support.google.com stop working. That's the conservative privacy choice and matches the brief.

## D7. Which AI/Google surfaces are removed at build level, and which in code
Each candidate was tried with `gn gen`:
- **Build level (works):** `enable_compose=false` (needed a small GN guard fix), `use_on_device_model_service=false`, `build_with_internal_optimization_guide=false`.
- **Kept on, disabled in code instead:**
  - `enable_screen_ai_service`: nine BUILD files assert on it, including the PDF service; removing it needs a ~1.6k-line guard patch. The ScreenAI library is a *downloaded component*, not shipped, so blocking its registration and download stops all traffic for far less upstream churn.
  - `enable_lens_desktop`: off is an unsupported desktop configuration, since `chrome/browser` depends on `ui/lens` unconditionally. Lens only works by uploading to Google, so its runtime features are turned off and its hosts are scrubbed.
- **Not available:** `enable_nacl` (NaCl is gone from our tree) and any `enable_glic` arg (Glic is runtime-gated only, so it's disabled through features in code).
- **Kept:** `safe_browsing_mode=1` (local protection lists remain available but default off; reporting/pings are disabled in code). `safe_browsing_mode=0` would need a ~4k-line guard patch across ~100 files. ungoogled does that, but it touches large parts of the browser and makes rebasing hard.
- **Kept:** `exclude_unwind_tables=false`. On mac, unwind tables are used by C++ and Objective-C exception propagation and by crash stack walks. The size win isn't worth a correctness risk we can't test yet.
- Follow-up: the first sync left `third_party/litert/src` fetched but unchecked-out. We checked out the DEPS-pinned commit by hand with `GIT_LFS_SKIP_SMUDGE=1`; its LFS objects are models and test data the build doesn't use.

## D8. Private default preferences, and the ones we left alone
- **Changed:** network prediction (preload/preconnect) off, background mode off, `<a ping>` auditing off, alternate error pages off (this also turns off captive-portal probes), search suggestions off, third-party cookies blocked, `canMakePayment` off, ask where to save downloads, WebRTC IP policy `default_public_interface_only`, autofill addresses/cards off.
- **WebRTC:** ungoogled uses `disable_non_proxied_udp`, which forces calls over TCP/TURN and degrades many web video-call apps. We pick `default_public_interface_only`: no private or local IPs leak (important because `enable_mdns=false` also removes mDNS candidate obfuscation), and UDP still works.
- **Kept on:** the password manager's offer to save, and auto sign-in. Both are local only (no sync without sign-in), and the brief says the password manager stays. Unique saved passwords are a security plus.
- **Kept:** the show-bookmark-bar default (cosmetic, no privacy value).
- **Kept:** DoH automatic mode, including the Google provider entry. Automatic mode only upgrades the resolver the user already has (e.g. system 8.8.8.8 → dns.google DoH), so it adds no new destination.
- **Not changed:** the IPv6 reachability probe "to 2001:4860:4860::8888". It's a UDP `connect()` that only selects a route; no packet is sent.
- **Not taken:** ungoogled's disable-download-quarantine. On macOS that removes Gatekeeper's quarantine attribute from downloads, a real security regression.

## D9. Phase 2 defaults
- **Fingerprinting noise (canvas readback, measureText, client rects): ON by default.** The brief says to ship the private choice. The perturbations are tiny (±1 on ~1/128 pixels; geometry scaled by 1±1e-6) and stable within a session. Each can be turned off in chrome://flags.
- **Battery Status API:** a fixed "charging, 100%" status, always (no flag).
- **Off by default, as opt-in flags:** everything that changes how pages work or look (WebGL info spoofing, reduced system info, no UA client hints, referrer trimming, popups-to-tabs, etc.). Chromium's default referrer policy (`strict-origin-when-cross-origin`) already trims cross-origin referrers to the origin. Stricter modes break some sites' CSRF and analytics checks, so they're opt-in.
- **CT enforcement on, SCT auditing off:** certificates must be CT-logged as in Chrome. The k-anonymous "hashdance" lookups to Google are disabled.
- **Expired flags stay usable**, so our long-lived `aib-*` options and upstream flags don't silently stop working.
- **Flag plumbing:** our features live in `components/aib` (browser and components), `third_party/blink/public/common/aib_features.h` (Blink) and the net/content/storage feature files (layers that can't depend on components). `aib/scripts/register_flag.py` writes the about_flags.cc entry, flag_descriptions.h, flag-metadata.json (owner `//components/aib/OWNERS`, expiry milestone 200) and enums.xml hashes.

## D10. Locales
- **Keep-list:** `aib_keep_locales` (a new GN arg in build/config/locales.gni) defaults to en-US plus 22 widely used languages (ar, de, en-GB, es, es-419, fr, hi, id, it, ja, ko, nl, pl, pt-BR, pt-PT, ru, sv, tr, uk, vi, zh-CN, zh-TW). Other system languages fall back to English UI. Set `aib_keep_locales = []` to ship all 54 desktop locales.
- **`translate_genders = false`:** Chromium 160 ships four packs per locale (default plus feminine, masculine and neuter variants for strings that address the user). We ship one, so those strings use the default wording. `gn gen` shows 92 locale bundle entries with gender variants versus 23 without; size deltas are measured in BENCHMARKS.md once built.

## D11. Performance build flags and runtime defaults
- **CPU target:** no `-mcpu` flag added. Our clang already uses `-target-cpu apple-m1` (ARMv8.4-A) for `arm64-apple-macos` (checked with `clang -###`), the baseline every Apple silicon Mac supports. No M5-only tuning, so one build runs everywhere.
- **Kept:** official + ThinLTO + PGO (D4), `symbol_level=0`, stripping.
- **Memory Saver default left off:** it only discards tabs after long inactivity, which our benchmark can't measure. The brief says changes without measured benefit get reverted, so we didn't make it.
- **`enable_on_device_translation=false` isn't a supported configuration** (live_caption depends on it unconditionally). TranslateKit's model component is unregistered instead (b253b4e63c), so no models download.
- **No sandbox, site-isolation or JIT-safety changes.** Nothing trades security for speed.

## D12. Build-time UI rebrand
`aib/scripts/rebrand_strings.py` rewrites "Chromium" → "AI Browser" in the branded string files and their translations at build time instead of committing those edits: every upstream roll touches the 80+ .xtb files, so committed edits would conflict constantly. grit computes the remapped translation IDs, and coverage was verified unchanged.
