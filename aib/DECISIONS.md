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
