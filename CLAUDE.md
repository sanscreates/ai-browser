# AI Browser: brief for Claude (Opus)

You are the lead engineer on **AI Browser**, a privacy-hardened, fast, lean browser built on our own fork of Chromium. This repo **is** that fork: `github.com/sanscreates/ai-browser`, forked from `github.com/chromium/chromium`. The local clone is shallow (`--depth 1`, branch `main`).

Work on your own. Nobody will be at the keyboard to answer questions. When you would normally ask, choose the conservative option, note the decision in `aib/DECISIONS.md`, and keep going.

---

## The mission

1. **Do everything ungoogled-chromium does to our fork, but write it ourselves.** Study the ungoogled-chromium repository (https://github.com/ungoogled-software/ungoogled-chromium) to find out *what* it changes and *why*. Then write our own implementation of each change against our tree. Don't fork it, vendor it, or copy its patch files in.
2. **Remove telemetry, Google phone-home traffic and the other odd extras**: metrics/UMA, crash upload, field trials, Safe Browsing pings, GCM/push to Google, domain reliability, RLZ, Google host detection, sign-in and sync to Google, translate pings, spelling-service pings, "hotword"/AI/Gemini/Lens/Compose surfaces, Privacy Sandbox/Topics/FLEDGE, promo/what's-new/NTP doodle fetches, the optimization-guide model downloads, component-updater calls to Google, and anything else the browser sends out without the user asking for it.
3. **Make it fast.** Tune the build and the runtime so it measurably beats stock Chromium of the same version on startup, page load, JS benchmarks and memory.
4. **Make it small.** Cut the shipped app size as far as it will go without breaking normal browsing.

### Licensing rules (read these first)
- ungoogled-chromium is **BSD-3-Clause**. Chromium itself is BSD-3-Clause plus many third-party licenses, and we have to ship *those* notices whatever we do (`tools/licenses/licenses.py` generates them).
- Ideas, feature lists and "what to disable" knowledge are not copyrightable. Read ungoogled's patches and lists to learn what to change, then **write our own code**: our own diffs, our own GN args, our own scripts.
- **Don't copy patch files, scripts or list files verbatim**, and don't do mechanical find-and-replace ports of them. Re-derive every change from Chromium's current source.
- If you ever reuse a non-trivial piece of their code or data anyway (for example a long list that can't reasonably be rebuilt), record it in `aib/THIRD_PARTY_NOTICES.md` with their BSD-3 notice. That's all the license asks for, and it's far better than a hidden violation. Never use the ungoogled-chromium name to endorse or promote our browser.
- Clone ungoogled-chromium **outside this repo** as a read-only reference: `git clone --depth 1 https://github.com/ungoogled-software/ungoogled-chromium ~/Downloads/ungoogled-reference`. Never add it as a submodule, subtree or remote.

---

## Machine and constraints (verified)
- Apple **M5**, arm64, 10 cores, 24 GB RAM, macOS 27.2.1.
- **About 87 GB free disk after the source clone** (the clone itself is ~7 GB, Chromium 160.0.8188.0). A full `gclient sync` plus a build can blow past that. Rules:
  - Run `df -h ~` before every large step. **Always leave at least 15 GB free.** If a step would cross that line, stop and write down what's needed in `aib/STATUS.md`.
  - Use `gclient sync --no-history --shallow` and skip optional deps (`checkout_nacl=False`, no Android/iOS/ChromeOS checkouts, and so on).
- **Full Xcode is NOT installed** (only Command Line Tools). macOS Chromium builds need full Xcode and the macOS SDK. Check with `xcode-select -p` / `xcodebuild -version`. If Xcode is still missing, **do all the source work anyway** and keep it syntax-correct (use `gn gen`/`gn check` where the toolchain allows). Then put "install Xcode from the App Store" at the top of `aib/STATUS.md` as the blocker for building. Don't try to install Xcode yourself.
- depot_tools: install into `~/depot_tools` (outside the repo) and put it on PATH for your shell sessions.
- Don't use sudo. Don't force-push `main`. Don't delete anything outside this repo except your own temp files.

---

## Repo layout and git workflow
- `main` mirrors upstream Chromium. **Don't commit our changes to `main`.**
- Do all work on the branch **`aib`**, created from the current `main` commit. Push it with `git push -u origin aib`. The clone is shallow, so pushes go on top of history GitHub already has. That's fine.
- **One logical change per commit**, with a prefix: `privacy:`, `telemetry:`, `perf:`, `size:`, `ui:`, `build:`, `branding:`. Small, focused commits are what let us rebase onto future Chromium releases.
- Put everything that is ours and isn't an in-tree source edit under `aib/`:
  - `aib/STATUS.md`: what's done, in progress and blocked. Keep it current; it's the first thing the owner reads.
  - `aib/FEATURES.md`: a table covering **every** ungoogled-chromium change you found. Columns: their change, what it does, our status (done / partial / skipped plus the reason), and our commit hash.
  - `aib/DECISIONS.md`: the judgment calls you made and why.
  - `aib/THIRD_PARTY_NOTICES.md`: see the licensing rules above.
  - `aib/args.gn`: the release build args, each line commented.
  - `aib/scripts/`: our own tooling (fetch deps, domain scrubbing, binary pruning, export patches, build, benchmark, size report).
  - `aib/patches/`: regenerate with `git format-patch main..aib -o aib/patches/` at milestones, so the changes can be carried to a fresh Chromium checkout.
  - `aib/BUILDING.md`: exact steps from a fresh machine to a signed `.app`.
  - `aib/BENCHMARKS.md`: measured results only.
- Push to `origin aib` after each milestone.

---

## Work plan (in order)

### Phase 0: Recon
1. Clone the ungoogled reference (see above). Read its `docs/`, `flags.gn`, `pruning.list`, `domain_regex.list`, `domain_substitution.list`, `patches/series` and every patch under `patches/core` and `patches/extra`. Also skim its macOS platform repo (`ungoogled-software/ungoogled-chromium-macos`) for Mac-specific changes.
2. Fill in `aib/FEATURES.md` with every change, grouped like this: build flags; binary pruning; domain substitution; core de-Googling patches; extra features and flags (`chrome://flags` additions such as fingerprinting noise, popups-to-tabs, close-window-with-last-tab, keep-old-history, and the rest); default prefs; macOS-specific.
3. Note the Chromium version we're on (`chrome/VERSION`) and compare it with the Chromium version ungoogled currently targets. APIs will have moved, so re-derive each change against **our** tree.

### Phase 1: De-Google and remove telemetry (our own implementation)
Reach parity with ungoogled's privacy behavior, written our way:
- **Build-level off switches first** (cleanest, and they also shrink the binary): e.g. `safe_browsing_mode=0`, `enable_reporting=false`, `enable_rlz=false`, `enable_hangout_services_extension=false`, `enable_mdns=false`, `enable_service_discovery=false`, `enable_remoting=false`, `use_official_google_api_keys=false`, empty `google_api_key`/`google_default_client_id`/`google_default_client_secret`, `disable_fieldtrial_testing_config=true`, `enable_nacl=false`, and the GN switches for Lens, Compose, Glic/Gemini, on-device models, screen AI, optimization guide models, and similar. Check every arg actually exists in our tree (`gn args out/x --list`). Don't invent args.
- **Code changes** wherever a build flag isn't enough: hard-disable metrics/UMA/UKM recording and upload, crash reporter upload, variations/field-trial fetch, GCM, domain reliability, Google host detection, Google URL tracker, sign-in and sync to Google, translate network calls (leave the UI usable without network or hide it), spelling-service, NTP remote content and promos, Privacy Sandbox (Topics/FLEDGE/Attribution), component-updater pings to Google, WebRTC log upload, the default extensions that phone home, and default prefs (search suggestions, URL-keyed anonymized data collection, network prediction/prefetch to Google, and so on).
- **Default search engine**: none (or DuckDuckGo). Remove Google's privileged hooks without breaking the ability to add Google manually.
- **Domain scrubbing**: write our own `aib/scripts/scrub_domains.py` that rewrites Google endpoints in source to a non-resolving placeholder TLD (pick our own, e.g. `.aib-invalid`), driven by a file list and regexes **we** generate from our tree. It must be reversible (keep a cache/manifest) so it can run before a build and be undone before a rebase. Don't commit scrubbed source; it runs at build time.
- **Binary pruning**: our own `aib/scripts/prune_binaries.py` plus a list generated from our tree, removing prebuilt binaries that aren't needed so the build comes from source.
- **Verify**: write `aib/scripts/net_audit.sh`. It launches a fresh profile with `--log-net-log` (or behind a local logging proxy), idles 5 minutes, opens a few sites, quits, and lists every host contacted that the user didn't ask for. The goal is **zero** unsolicited requests. Record results in `aib/STATUS.md`. (This needs a working build; if building is blocked, write the script and mark it pending.)

### Phase 2: ungoogled's extra features and flags
Write our own versions of their useful `chrome://flags`/command-line additions: fingerprinting mitigations, popups-to-tabs, close-window-with-last-tab, keep-old-history, show-avatar-button, scroll-tabs, extension install from CRX/web store tweaks, referrer trimming, and the rest. Wherever a choice is involved, ship the safe/private default.

### Phase 3: Performance
Build tuning, applied carefully and checked against what our tree supports:
- `is_official_build=true`, `is_debug=false`, `dcheck_always_on=false`, `is_component_build=false`.
- **Keep PGO on** (`chrome_pgo_phase=2`, with the official profiles fetched via `checkout_pgo_profiles`). It's one of the biggest speed wins, so don't disable it the way ungoogled does. If fetching the profiles needs a Google storage download at *build* time, that's acceptable; the browser at runtime is what has to be clean. Record this in DECISIONS.md.
- ThinLTO, ICF, `symbol_level=0`, `blink_symbol_level=0`, `v8_symbol_level=0`, `enable_stripping=true`, `exclude_unwind_tables` where safe on mac.
- Target Apple silicon (`target_cpu="arm64"`). Look into tuning for newer Apple cores (`-mcpu=apple-m1` baseline, which every Apple silicon Mac supports). Don't target M5-only instructions unless you also ship a baseline build.
- Runtime: remove background work that was only there for telemetry or Google services, and audit startup for the stuff we've stripped (lazy-load or drop it). Consider sensible defaults: a tab discarding/memory saver policy, and keeping preconnect only where it helps the user, never to Google. Don't turn on unsafe flags (e.g. `--no-sandbox`, `--disable-site-isolation-trials`), and keep site isolation and the sandbox intact. **Security is not traded for speed.**
- Write `aib/scripts/bench.sh`, which runs Speedometer 3, JetStream 2 and MotionMark, a cold/warm startup time, and idle/10-tab memory. It compares against a stock Chromium build of the **same version** (download the matching official snapshot) and writes to `aib/BENCHMARKS.md`. **Report only numbers you measured.** A change that doesn't measurably help gets reverted.

### Phase 4: Size
- Measure the `.app` size before and after each size change (`aib/scripts/size_report.sh`: total `.app`, the framework binary, `.pak`s, locales).
- Levers: everything the Phase 1 build flags remove, plus dropping unneeded locales (a configurable keep-list, default en-US plus the major languages), the dead component extensions, test/dev-only resources, unused codecs/features with clear reasoning, and stripped symbols. Keep the dSYMs separately if needed.
- Don't remove things that break normal browsing: PDF viewer, media playback, extensions, DevTools, printing and password manager stay unless you write down why.
- Log every size change with its measured delta in `aib/BENCHMARKS.md`.

### Phase 5: Branding and packaging
- Product name "AI Browser" via our own branding (`chrome/app/theme/` and `BRANDING`-style files). Bundle ID `com.sanscreates.aibrowser`. Use a placeholder icon for now.
- `aib/BUILDING.md` with exact commands; `aib/scripts/build.sh` that does fetch deps → prune → scrub → gn gen with `aib/args.gn` → autoninja → unscrub → package.

---

## How to work
- Chromium ships its own agent docs in `agents/` (see `agents/README.md`, `agents/ai_policy.md`, `agents/skills/`). Use them for Chromium dev know-how; this brief wins wherever they conflict.
- Read before you edit. Chromium is huge: use `git grep` and `gn desc`/`gn refs` rather than guessing.
- After each change, build what you can (or at least run `gn gen` and compile the affected targets once a toolchain is available) and make sure you haven't broken the build.
- Never claim something works, is faster or is smaller without evidence you produced. Put the evidence in the docs.
- Keep `aib/STATUS.md` updated as you go, so you can pick up where you left off if interrupted. At the start of each session, read `aib/STATUS.md` and `git log main..aib --oneline` first.
- If you hit a hard blocker (disk, Xcode, a broken upstream), document it precisely in STATUS.md, then keep working on whatever isn't blocked.
