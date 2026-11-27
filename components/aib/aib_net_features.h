// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef COMPONENTS_AIB_AIB_NET_FEATURES_H_
#define COMPONENTS_AIB_AIB_NET_FEATURES_H_

#include "base/feature_list.h"
#include "base/metrics/field_trial_params.h"
#include "components/aib/aib_features_export.h"

// AI Browser network, privacy and history switches. All are off by default so
// that the default behavior matches upstream. Options that net/ or the network
// service read live in net/base/features.h instead, because those layers must
// not depend on this component.
namespace aib::features {

// Local browsing history is never expired (upstream drops it after 90 days).
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibKeepOldHistory);

// Internationalized hostnames are always displayed in punycode.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibForcePunycodeHostnames);

// Websites can't add search engines on their own, neither from form
// submissions nor from OpenSearch description documents.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibDisableSearchEngineCollection);

// Changes how CRX (extension) downloads from websites are handled. The "mode"
// param is "download-as-file" or "always-prompt-install".
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibExtensionMimeHandling);
// True if CRX downloads from websites should be saved as regular files.
AIB_FEATURES_EXPORT bool ShouldDownloadCrxAsRegularFile();
// True if CRX downloads from any website should open the install prompt.
AIB_FEATURES_EXPORT bool ShouldAlwaysPromptForCrxInstall();

// History, cookies and site data, cache, download history and autofill form
// data are cleared when the profile closes.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibClearDataOnExit);

// beforeunload dialogs are never shown; leaving a page always proceeds.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibDisableBeforeUnload);

// When the V8 optimizer content setting is blocked for a site (or by
// default), that site's renderer also runs fully jitless.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibJitlessWhenJsOptimizerOff);

// Limits omnibox suggestions to search suggestions and the typed URL, plus
// optionally bookmarks and built-in pages. The "sources" param is one of
// "search", "search-bookmarks", "search-chrome", "search-bookmarks-chrome".
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibOmniboxAutocompleteFiltering);
// Only meaningful while kAibOmniboxAutocompleteFiltering is enabled.
AIB_FEATURES_EXPORT bool AibOmniboxFilteringAllowsBookmarks();
AIB_FEATURES_EXPORT bool AibOmniboxFilteringAllowsBuiltinPages();

}  // namespace aib::features

#endif  // COMPONENTS_AIB_AIB_NET_FEATURES_H_
