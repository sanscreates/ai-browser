# ungoogled-chromium feature parity

Every change found in ungoogled-chromium 158.0.8127.88 (`patches/series`, `flags.gn`, the list files, and the macOS repo), with what AI Browser (Chromium 160.0.8188.0) does about each. We re-derive every change against our own tree; none of their patch files or lists are copied.

Status: **done** (implemented; the commit is named), **partial**, **skipped** (with reason), **todo**.
"Build-verified" means the change compiled in our tree; until a full build exists, changes are only `gn gen`-checked. See STATUS.md.

## 1. Build flags (`flags.gn`)

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| `safe_browsing_mode=0` | Compiles out Safe Browsing | **skipped**: needs a ~4k-line, ~100-file guard patch in our tree. We keep mode 1 and turn off SB reporting/pings in code (DECISIONS D7) | — |
| `enable_reporting=false` | Removes the Reporting API / NEL uploads | done | args.gn |
| `enable_hangout_services_extension=false` | Removes the Hangouts component extension | done | args.gn |
| `enable_mdns=false`, `enable_service_discovery=false` | Removes mDNS/DNS-SD LAN discovery | done (gn-verified; compile pending) | args.gn |
| `enable_remoting=false` | Removes the CRD host | done | args.gn |
| `use_official_google_api_keys=false`, empty `google_api_key`/`client_id`/`client_secret` | No Google API keys baked in | done | args.gn |
| `disable_fieldtrial_testing_config=true` | No built-in field-trial config | done | args.gn |
| `enable_widevine=true` | Widevine support | done (same) | args.gn |
| `exclude_unwind_tables=true` | Smaller binary | **skipped** on mac for now: unwind info is used by C++/ObjC exception handling and crash stacks (D7) | — |
| `chrome_pgo_phase=0` | Their builds skip PGO | **deliberately different**: we keep `chrome_pgo_phase=2` (D4) | args.gn |
| `clang_use_chrome_plugins=false`, `treat_warnings_as_errors=false` | Their custom toolchain | We use the stock toolchain, so we keep the plugins; `treat_warnings_as_errors=false` is kept | args.gn |
| `use_unofficial_version_number=false` | Version string | default kept | — |
| `v8_drumbrake_bounds_checks=true` | For their DrumBrake (jitless wasm) option | skipped: we don't enable DrumBrake | — |
| mac `flags.macos.gn` (official, thin LTO, PGO 2, `enable_updater=false`, proprietary codecs, ffmpeg Chrome) | Release config | done (equivalents in args.gn; `symbol_level=0` instead of 1) | args.gn |
| (ours) `enable_rlz=false`, `enable_compose=false`, `use_on_device_model_service=false`, `build_with_internal_optimization_guide=false` | AI and tracking surfaces at build level | done | args.gn + compose GN fix |

## 2. Binary pruning (`pruning.list`, `utils/prune_binaries.py`)

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| pruning.list (~11.8k prebuilt/binary files) and contingent paths (prebuilt toolchains) | Forces build-from-source and drops test data | done, our own: `aib/scripts/prune_binaries.py` with a list generated from our tree (691 files, ~1.4 GB) that skips the stock toolchain and anything the generated ninja files reference | b743aea2e3 |

## 3. Domain substitution (`domain_regex.list`, `domain_substitution.list`)

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| Regex rewrite of Google/YouTube/etc. hosts to leetspeak `*.qjz9zk` in ~17k files | Any leftover endpoint can't resolve | done, our own design: `aib/scripts/scrub_domains.py` appends `.aib-invalid`, curated `aib/domains/domains.txt`, file list generated from our tree, reversible with a sha256 manifest (D6) | scrubber commit |
| `block-trk-and-subdomains` (`trk:` scheme; blocks `*.qjz9zk`) | Blocks and logs requests to scrubbed hosts | done, our own: net refuses to resolve or fetch `*.aib-invalid` (logged as `aib_scrubbed_host` in NetLog) | 131773ec24 |
| `fix-learn-doubleclick-hsts` | Keeps the HSTS generator happy after substitution | not needed: we never scrub the HSTS preload JSON | — |

## 4. Core de-Googling patches

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| inox 0001 / ungoogled fix-building-without-safebrowsing, move-js-optimizer-unfamiliar-sites, remove-unused-preferences-fields, macOS fix-disabling-safebrowsing | Make `safe_browsing_mode=0` build, then strip SB/sign-in prefs | skipped (we keep mode 1; see section 1) | — |
| inox 0003 disable-autofill-download-manager | No autofill crowdsourcing queries/uploads | done | c3fda340ed |
| inox 0005 disable-default-extensions | No Web Store hosted app or payments component app; no CWS install path | already off in our tree: kWebstoreHostedApp is disabled outside ChromeOS and the payments app is branded-only | — |
| inox 0015 disable-update-pings | Standalone updater returns no URLs | covered: `enable_updater=false`, and the updater isn't built. Component updater handled separately | args.gn |
| inox 0021 disable-rlz | Removes RLZ | done (`enable_rlz=false`) | args.gn |
| iridium safe_browsing-disable-incident-reporting | No SB incident reports or extended-reporting opt-in | done (plus SB off by default and no reporting opt-in) | f581b2f97f, 0d7a26ce42 |
| iridium safe_browsing-disable-reporting-of-safebrowsing-over | No client-side phishing pings | done | f581b2f97f |
| disable-crash-reporter (+ macOS disable-crashpad-handler) | No crash upload | done: no upload URL, handler ignores --url, consent never given. Crashpad still writes local dumps | 4547a89ccf, feed8b6fcc |
| disable-google-host-detection | No Google-only behavior (X-Client-Data, etc.) | partial: X-Client-Data never sent. The remaining Google-host logic is policy-driven (SafeSearch/YouTube restrict) or needs sign-in, so it was left alone | e7e8085813 |
| replace-google-search-engine-with-nosearch | No Google default search | done, differently: DuckDuckGo is the default and Google stays selectable; search tracking params removed | 21b0bfbf0c, 8784bac4f7 |
| toggle-translation-via-switch | Translate off unless the user supplies a server | done: Translate needs --translate-script-url; no language-list or ranker fetches | f410471ee4 |
| disable-untraceable-urls | RLZ financial ping URL | covered by `enable_rlz=false` | args.gn |
| disable-profile-avatar-downloading | No gstatic avatar fetches | skipped: only on explicit user action, and the gstatic host is scrubbed and blocked | 131773ec24 |
| disable-gcm | No GCM/MCS to mtalk.google.com | done | 0c38d8e4fb |
| disable-domain-reliability | No Domain Reliability beacons | done | 517c372f8b |
| disable-gaia | No GaiaAuthFetcher traffic | done via sign-in off by default (no DICE or Gaia cookie fetches) | 79db114923 |
| disable-fonts-googleapis-references | Reader mode CSP/fonts from Google | done (distiller viewer) | df0dff83b9 |
| disable-webstore-urls | No CWS auto-update URL fill-in, etc. | partial: no Web Store URL fill-in for extensions without update_url | c9258db202 |
| disable-webrtc-log-uploader | No WebRTC log upload | done (collection off by default; Hangouts extension not built) | ed0992ed24 |
| disable-ai | Strips ScreenAI, Glic actor/skills, on-device model consumers | done: Glic/actor/skills/Lens off, Optimization Guide off, AI and model components unregistered, compose and on-device model off at build level | 739e15d887, 7b9510e042, b253b4e63c, args.gn |
| fix-building-with-prunned-binaries | Build fixes after pruning | handle when pruning lands | |
| disable-network-time-tracker | No Google time queries | done | 35ebe52dd9 |
| disable-mei-preload | No Media Engagement preload component | done (component no longer registered; bundled data removed in the size phase) | b253b4e63c |
| block-requests | One Google bar, NTP backgrounds, brandcode, hunspell, affiliation, ranker, update_client, DevTools CSS data | done: affiliation, ranker, component update loop, DevTools remote CSS data; One Google bar and NTP backgrounds unreachable with the local NTP; hunspell download not used on mac; brandcode fetch is Windows reset-prompt only | 282db3993e, f410471ee4, 3adff39671, b595bb8b56, f3bd1af77f |
| disable-privacy-sandbox | Drops the attestations preload component | already off upstream: no Privacy Sandbox ad API is enabled by default in Chromium 160 (verified), and the attestations preload is gone | — |
| doh-changes | DoH defaults off, no Google DoH entries, no google.com probe | partial: DNS probe uses example.com; DoH automatic mode kept (D8) | d7fc801a09 |
| extensions-manifestv2 | Keep MV2 extensions working | done | ea522d5117 |
| remove-f1-shortcut | F1 no longer opens Google help | done | 73640e63e2 |
| remove-navigation-source-param | No `source=chrome.ob` in search URLs | done (also aqs/gs_lcrp and psi) | 8784bac4f7 |
| bromite disable-fetching-field-trials | Never fetch the variations seed | done | 0d656f1c52 |
| upstream-fixes (wasm interpreter, missing deps) | Their build fixes | not applicable to our tree (already upstream or DrumBrake-only) | — |

## 5. Extra features and flags

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| add-ungoogled-flag-headers, add-components-ungoogled | Flag plumbing | done, our own: features in components/aib and blink aib_features.h, registered in about_flags.cc with metadata and enums by aib/scripts/register_flag.py | 978fdb26fe, ad236769c0, 97d4cd20c4 |
| inox 0006 modify-default-prefs | Private defaults (no search suggest, no hyperlink auditing, 3P cookies blocked, …) | partial: private defaults done; password-manager defaults kept (D8) | 1fba7e9b26 |
| inox 0008 restore-classic-ntp | Local NTP, not the search engine's | done (always the local NTP) | f3bd1af77f |
| inox 0013 + debian google-api-warning | No missing-API-key infobar | done | 8375ea5967 |
| inox 0016 chromium-sandbox-pie | Linux SUID sandbox PIE | skipped: Linux only | — |
| inox 0019 disable-battery-status-service | Battery API returns defaults (fingerprinting) | done (fixed status, no platform monitor) | 0918a5c363 |
| iridium mime_util text/x-suse-ymp | Download YaST files | skipped: openSUSE-specific, no value on mac | — |
| iridium prompt-for-download-directory | Ask where to save | done | 1fba7e9b26 |
| iridium updater-disable-auto-update | Mac Keystone interval 0 | not applicable: the Keystone interval code is branded-only | — |
| iridium Remove-EV-certificates | No EV UI treatment | skipped: Chrome no longer shows any EV treatment in the address bar; the EV metadata only feeds the certificate viewer | — |
| iridium disable-profile-auto-import-on-first-run | No silent import from other browsers | done | ec8a00a167 |
| bromite fingerprinting client-rects / measureText noise | Flags for fingerprint noise | done, ON by default (private default) | 8b14f547d3, 97d4cd20c4 |
| bromite flag-max-connections-per-host | Flag | done (feature with param, applied inside the network service) | 4a346a04b1 |
| bromite canvas image-data noise | Flag | done, ON by default | 97d4cd20c4 |
| disable-formatting-in-omnibox | Show full URLs | done (full URLs by default; status-bubble delay unchanged) | df3349d796 |
| add-ipv6-probing-option | No IPv6 probe to Google DNS | skipped: the probe is a UDP connect(), so no packet is sent (D8) | — |
| remove-disable-setuid-sandbox-as-bad-flag | Linux | skipped: Linux only | — |
| disable-intranet-redirect-detector | No random-host DNS probes | done | 6ad2cae1b1 |
| disable-download-quarantine | No quarantine xattr | **skipped**: on macOS this disables Gatekeeper checks on downloads, a security regression (D8) | — |
| fix-building-without-mdns-and-service-discovery | Build fix | todo if the compile needs it | |
| add-flag-to-configure-extension-downloading | CRX download handling | done | afb42cd2d9 |
| add-flag-for-search-engine-collection | Stop auto-adding search engines | done | a920569756 |
| add-flag-to-disable-beforeunload | Flag | done | 3f305e6ba3 |
| add-flag-to-force-punycode-hostnames | Flag | done | eea3336a63 |
| add-flag-to-show-avatar-button | Flag | done | 84f732a172 |
| add-suggestions-url-field | Settings UI field | skipped for now: settings UI work across 4 layers; suggestions are off by default, so low value | — |
| add-flag-to-hide-crashed-bubble | Flag | done | 34ce479fc9 |
| add-flag-to-scroll-tabs | Flag | done | 1773223fb2 |
| enable-paste-and-go-new-tab-button | Middle-click new-tab button pastes and goes | done (also on macOS, using the regular clipboard) | 30723142a1 |
| add-flag-for-bookmark-bar-ntp | Flag | done | f34ec2d82a |
| enable-menu-on-reload-button | Reload menu always | done | 0bd3736ce1 |
| add-flag-for-omnibox-autocomplete-filtering | Flag | done | 492da57825 |
| disable-dial-repeating-discovery | No periodic SSDP | done | 1c6c77761e |
| remove-uneeded-ui | Hide Google-pointing UI | partial: AI settings and shortcuts gone via features; Google help links point at scrubbed hosts. Per-page Lit settings edits deferred | 6ba07f19f2 |
| add-flag-to-close-window-with-last-tab | Flag | done | 596b79b1bc |
| add-flag-to-convert-popups-to-tabs | Flag | done | ad236769c0 |
| add-flag-to-disable-local-history-expiration | `--keep-old-history` | done | 978fdb26fe |
| add-extra-channel-info | about:version branding | todo (branding phase) | |
| prepopulated-search-engines | No starter-pack expansion | partial: AI starter packs (@gemini/@aimode/@page) removed; the history/tabs/bookmarks starter packs are kept because they are local | 6ba07f19f2 |
| add-flag-to-clear-data-on-exit | Flag | done | 2074864fd1 |
| add-flag-for-qr-generator | Flag | skipped: QR generation is local and has no privacy impact | — |
| add-flag-for-grab-handle | Flag | done | 1da6fc5605 |
| add-flag-for-close-confirmation | Flag | done | 8d999be321 |
| keep-expired-flags | Expired flags stay usable | done | a1c8558a3e |
| add-flag-for-custom-ntp | Flag | done (text box) | 9655c0dd17 |
| add-flag-for-tab-hover-cards | Flag | done | 1a9ccc1c5e |
| add-flag-to-hide-tab-close-buttons | Flag | done | 1a9ccc1c5e |
| add-flag-to-disable-tls-grease | Flag | done | c0d3a8608b |
| add-flag-to-change-http-accept-header | Flag | done | a1d181f926 |
| add-flag-for-disabling-link-drag | Flag | done | daa05da0df |
| add-flag-to-hide-extensions-menu | Flag | done | c814b31e3e |
| add-flag-to-hide-fullscreen-exit-ui | Flag | done | f254055275 |
| add-flag-for-incognito-themes | Flag | done | de1104c3d4 |
| add-flags-for-referrer-customization | Referrer trimming flags | done (no-cross-origin / minimal), applied in net for every request | f713756a31 |
| default-webrtc-ip-handling-policy | `disable_non_proxied_udp` default | done, differently: default_public_interface_only (D8) | 1fba7e9b26 |
| add-flags-for-existing-switches | Expose existing switches in chrome://flags | done (proxy server/bypass, no-pings, start maximized, incognito, force dark mode, low-end mode) | 9e0dbc1158 |
| first-run-page | Help page on first run | skipped: their page explains ungoogled-specific workarounds; we revisit when branding the first run | — |
| add-flag-to-reduce-system-info | Flag | done | 068ffd5e28 |
| add-flag-to-remove-client-hints | Flag | done (UA client hints) | a31019c6a7 |
| enable-extra-locales | More UI locales | skipped: conflicts with our size goal (locale keep-list) | — |
| remove-pac-size-limit | No PAC size cap | done | dcb12990d3 |
| enable-certificate-transparency-and-add-flag | CT enforcement on | done (enforced; SCT auditing hashdance off) | 2a326a7e2b |
| add-flag-to-spoof-webgl-renderer-info | Flag | done | 6346596f42 |
| add-flag-to-increase-incognito-storage-quota | Flag | done | 67a347fbd2 |
| add-credits | Credit in chrome://credits | not needed: we reuse none of their code or data (see THIRD_PARTY_NOTICES.md) | — |
| disable-ai-search-shortcuts | No @gemini/@aimode | done | 6ba07f19f2 |
| disable-fedcm-by-default | FedCM off | done | cb48251270 |
| bundle-hyphenation-patterns | Bundle hyphenation data | skipped: macOS uses system hyphenation | — |
| add-flag-for-disabling-jit | Flag | done (jitless when the V8 optimizer setting is off) | 6af7074a3a |
| add-flag-to-hide-window-buttons | Flag | skipped: hiding macOS traffic lights has no privacy value and is fragile across macOS versions | — |

## 6. Default prefs (`docs/default_settings.md`)
Covered by inox 0006, iridium download prompt, default-webrtc-ip-handling-policy, disable-fedcm-by-default and doh-changes above.

## 7. macOS-specific (ungoogled-chromium-macos)

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| Toolchain patches (bindgen, clang version check, rust, esbuild, typescript, python, dsymutil, nasm, crubit, complex builtins, symbol order, …) | Needed for their system/pruned toolchain | not applicable: we use the stock gclient toolchain (verified: `//base` builds with Xcode 27 SDK) | — |
| disable-crashpad-handler | No crashpad process | done differently: the handler stays for local crash dumps but never uploads (no URL; --url ignored; consent never given) | 4547a89ccf |
| set-bundle-identifier | Custom bundle id | done (com.sanscreates.aibrowser) | d4374ba6cb |
| add-local-network-usage-description | `NSLocalNetworkUsageDescription` | done | d4374ba6cb |
| sign_and_package_app.sh, entitlements | Signing, notarization, DMG | todo (`aib/scripts/build.sh` package step, BUILDING.md) | |

## 8. Beyond ungoogled-chromium

| Our change | What it does | Our status | Commit |
|---|---|---|---|
| Built-in ad and tracker blocker | uBlock Origin 1.77.4 (Manifest V2, full `webRequestBlocking`) ships as a component extension that can't be removed or disabled, with an always-pinned toolbar button: blocked counts, domains, logger, and a per-site on/off switch. Off everywhere via `chrome://flags/#aib-content-blocker`. Denied Chromium's component-extension privileges (D13) | done (compiles; runtime check pending the full build) | 32ff695e3c, c778ecbbb1, e42e2c1ffa, 4c8284e48a |
