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
| pruning.list (~11.8k prebuilt/binary files) and contingent paths (prebuilt toolchains) | Forces build-from-source and drops test data | todo: our own `aib/scripts/prune_binaries.py` with a list generated from our tree. We keep the stock toolchain (clang/rust/node/esbuild prebuilts from DEPS), since we build with gclient rather than a system toolchain | |

## 3. Domain substitution (`domain_regex.list`, `domain_substitution.list`)

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| Regex rewrite of Google/YouTube/etc. hosts to leetspeak `*.qjz9zk` in ~17k files | Any leftover endpoint can't resolve | done, our own design: `aib/scripts/scrub_domains.py` appends `.aib-invalid`, curated `aib/domains/domains.txt`, file list generated from our tree, reversible with a sha256 manifest (D6) | scrubber commit |
| `block-trk-and-subdomains` (`trk:` scheme; blocks `*.qjz9zk`) | Blocks and logs requests to scrubbed hosts | todo: our version refuses to resolve or fetch `*.aib-invalid` in net | |
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
| add-ungoogled-flag-headers, add-components-ungoogled | Flag plumbing | todo: our own `components/aib` switches component; flags are registered in `about_flags.cc` | |
| inox 0006 modify-default-prefs | Private defaults (no search suggest, no hyperlink auditing, 3P cookies blocked, …) | partial: private defaults done; password-manager defaults kept (D8) | 1fba7e9b26 |
| inox 0008 restore-classic-ntp | Local NTP, not the search engine's | done (always the local NTP) | f3bd1af77f |
| inox 0013 + debian google-api-warning | No missing-API-key infobar | done | 8375ea5967 |
| inox 0016 chromium-sandbox-pie | Linux SUID sandbox PIE | skipped: Linux only | — |
| inox 0019 disable-battery-status-service | Battery API returns defaults (fingerprinting) | todo | |
| iridium mime_util text/x-suse-ymp | Download YaST files | skipped: openSUSE-specific, no value on mac | — |
| iridium prompt-for-download-directory | Ask where to save | done | 1fba7e9b26 |
| iridium updater-disable-auto-update | Mac Keystone interval 0 | not applicable: the Keystone interval code is branded-only | — |
| iridium Remove-EV-certificates | No EV UI treatment | todo | |
| iridium disable-profile-auto-import-on-first-run | No silent import from other browsers | done | ec8a00a167 |
| bromite fingerprinting client-rects / measureText noise | Flags for fingerprint noise | todo | |
| bromite flag-max-connections-per-host | Flag | todo | |
| bromite canvas image-data noise | Flag | todo | |
| disable-formatting-in-omnibox | Show full URLs | todo | |
| add-ipv6-probing-option | No IPv6 probe to Google DNS | skipped: the probe is a UDP connect(), so no packet is sent (D8) | — |
| remove-disable-setuid-sandbox-as-bad-flag | Linux | skipped: Linux only | — |
| disable-intranet-redirect-detector | No random-host DNS probes | done | 6ad2cae1b1 |
| disable-download-quarantine | No quarantine xattr | **skipped**: on macOS this disables Gatekeeper checks on downloads, a security regression (D8) | — |
| fix-building-without-mdns-and-service-discovery | Build fix | todo if the compile needs it | |
| add-flag-to-configure-extension-downloading | CRX download handling | todo | |
| add-flag-for-search-engine-collection | Stop auto-adding search engines | todo | |
| add-flag-to-disable-beforeunload | Flag | todo | |
| add-flag-to-force-punycode-hostnames | Flag | todo | |
| add-flag-to-show-avatar-button | Flag | todo | |
| add-suggestions-url-field | Settings UI field | todo | |
| add-flag-to-hide-crashed-bubble | Flag | todo | |
| add-flag-to-scroll-tabs | Flag | todo | |
| enable-paste-and-go-new-tab-button | Middle-click new-tab button pastes and goes | todo | |
| add-flag-for-bookmark-bar-ntp | Flag | todo | |
| enable-menu-on-reload-button | Reload menu always | todo | |
| add-flag-for-omnibox-autocomplete-filtering | Flag | todo | |
| disable-dial-repeating-discovery | No periodic SSDP | done | 1c6c77761e |
| remove-uneeded-ui | Hide Google-pointing UI | todo | |
| add-flag-to-close-window-with-last-tab | Flag | todo | |
| add-flag-to-convert-popups-to-tabs | Flag | todo | |
| add-flag-to-disable-local-history-expiration | `--keep-old-history` | todo | |
| add-extra-channel-info | about:version branding | todo (branding phase) | |
| prepopulated-search-engines | No starter-pack expansion | todo | |
| add-flag-to-clear-data-on-exit | Flag | todo | |
| add-flag-for-qr-generator | Flag | todo | |
| add-flag-for-grab-handle | Flag | todo | |
| add-flag-for-close-confirmation | Flag | todo | |
| keep-expired-flags | Expired flags stay usable | todo | |
| add-flag-for-custom-ntp | Flag | todo | |
| add-flag-for-tab-hover-cards | Flag | todo | |
| add-flag-to-hide-tab-close-buttons | Flag | todo | |
| add-flag-to-disable-tls-grease | Flag | todo | |
| add-flag-to-change-http-accept-header | Flag | todo | |
| add-flag-for-disabling-link-drag | Flag | todo | |
| add-flag-to-hide-extensions-menu | Flag | todo | |
| add-flag-to-hide-fullscreen-exit-ui | Flag | todo | |
| add-flag-for-incognito-themes | Flag | todo | |
| add-flags-for-referrer-customization | Referrer trimming flags | todo | |
| default-webrtc-ip-handling-policy | `disable_non_proxied_udp` default | done, differently: default_public_interface_only (D8) | 1fba7e9b26 |
| add-flags-for-existing-switches | Expose existing switches in chrome://flags | todo | |
| first-run-page | Help page on first run | todo | |
| add-flag-to-reduce-system-info | Flag | todo | |
| add-flag-to-remove-client-hints | Flag | todo | |
| enable-extra-locales | More UI locales | skipped: conflicts with our size goal (locale keep-list) | — |
| remove-pac-size-limit | No PAC size cap | todo | |
| enable-certificate-transparency-and-add-flag | CT enforcement on | todo | |
| add-flag-to-spoof-webgl-renderer-info | Flag | todo | |
| add-flag-to-increase-incognito-storage-quota | Flag | todo | |
| add-credits | Credit in chrome://credits | todo (only if we reuse any of their code) | |
| disable-ai-search-shortcuts | No @gemini/@aimode | done: Glic/actor/skills/Lens off, Optimization Guide off, AI and model components unregistered, compose and on-device model off at build level | 739e15d887, 7b9510e042, b253b4e63c, args.gn |
| disable-fedcm-by-default | FedCM off | done | cb48251270 |
| bundle-hyphenation-patterns | Bundle hyphenation data | skipped: macOS uses system hyphenation | — |
| add-flag-for-disabling-jit | Flag | todo | |
| add-flag-to-hide-window-buttons | Flag | todo | |

## 6. Default prefs (`docs/default_settings.md`)
Covered by inox 0006, iridium download prompt, default-webrtc-ip-handling-policy, disable-fedcm-by-default and doh-changes above.

## 7. macOS-specific (ungoogled-chromium-macos)

| Their change | What it does | Our status | Commit |
|---|---|---|---|
| Toolchain patches (bindgen, clang version check, rust, esbuild, typescript, python, dsymutil, nasm, crubit, complex builtins, symbol order, …) | Needed for their system/pruned toolchain | not applicable: we use the stock gclient toolchain (verified: `//base` builds with Xcode 27 SDK) | — |
| disable-crashpad-handler | No crashpad process | todo (see disable-crash-reporter) | |
| set-bundle-identifier | Custom bundle id | done (com.sanscreates.aibrowser) | d4374ba6cb |
| add-local-network-usage-description | `NSLocalNetworkUsageDescription` | done | d4374ba6cb |
| sign_and_package_app.sh, entitlements | Signing, notarization, DMG | todo (`aib/scripts/build.sh` package step, BUILDING.md) | |
