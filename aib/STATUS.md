# AI Browser: status

_Updated by Claude as work progresses. Read this first._

- Base: Chromium 160.0.8188.0 (upstream `main` @ 7d0cc1fc42), shallow clone.
- ungoogled-chromium reference: 158.0.8127.88 (cloned read-only at `~/Downloads/ungoogled-reference`, macOS repo at `~/Downloads/ungoogled-reference-macos`).
- Branch: `aib` (all our work). `main` mirrors upstream.
- Repo location: `~/aib-build/src` (`~/Downloads/AI browser` is a symlink to it; see DECISIONS D1).

## Blockers
- (none hard yet) Xcode: not installed in /Applications, but `~/Downloads/Xcode.app` (27.0) works via `DEVELOPER_DIR` (DECISIONS D2).

## Done
- Repo forked, brief written (CLAUDE.md).
- depot_tools in `~/depot_tools`; ungoogled reference clones in place.
- `aib/scripts/fetch_deps.sh` (gclient root, unmanaged solution, disk watchdog).

## In progress
- Phase 0: recon of ungoogled-chromium patches → `aib/FEATURES.md`.
- `gclient sync --no-history --shallow` running (log: `~/aib-build/sync.log`).
