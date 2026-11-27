// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "components/aib/aib_net_features.h"

namespace aib::features {

namespace {

enum class CrxHandlingMode {
  kDownloadAsFile,
  kAlwaysPromptInstall,
};

constexpr base::FeatureParam<CrxHandlingMode>::Option
    kCrxHandlingModeOptions[] = {
        {CrxHandlingMode::kDownloadAsFile, "download-as-file"},
        {CrxHandlingMode::kAlwaysPromptInstall, "always-prompt-install"},
};

enum class OmniboxSources {
  kSearch,
  kSearchBookmarks,
  kSearchChrome,
  kSearchBookmarksChrome,
};

constexpr base::FeatureParam<OmniboxSources>::Option
    kOmniboxSourcesOptions[] = {
        {OmniboxSources::kSearch, "search"},
        {OmniboxSources::kSearchBookmarks, "search-bookmarks"},
        {OmniboxSources::kSearchChrome, "search-chrome"},
        {OmniboxSources::kSearchBookmarksChrome, "search-bookmarks-chrome"},
};

}  // namespace

BASE_FEATURE(kAibKeepOldHistory, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibForcePunycodeHostnames, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibDisableSearchEngineCollection,
             base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibExtensionMimeHandling, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE_ENUM_PARAM(CrxHandlingMode,
                        kAibExtensionMimeHandlingMode,
                        &kAibExtensionMimeHandling,
                        "mode",
                        CrxHandlingMode::kAlwaysPromptInstall,
                        &kCrxHandlingModeOptions);

bool ShouldDownloadCrxAsRegularFile() {
  return base::FeatureList::IsEnabled(kAibExtensionMimeHandling) &&
         kAibExtensionMimeHandlingMode.Get() ==
             CrxHandlingMode::kDownloadAsFile;
}

bool ShouldAlwaysPromptForCrxInstall() {
  return base::FeatureList::IsEnabled(kAibExtensionMimeHandling) &&
         kAibExtensionMimeHandlingMode.Get() ==
             CrxHandlingMode::kAlwaysPromptInstall;
}

BASE_FEATURE(kAibClearDataOnExit, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibDisableBeforeUnload, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibJitlessWhenJsOptimizerOff, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibOmniboxAutocompleteFiltering,
             base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE_ENUM_PARAM(OmniboxSources,
                        kAibOmniboxAutocompleteFilteringSources,
                        &kAibOmniboxAutocompleteFiltering,
                        "sources",
                        OmniboxSources::kSearch,
                        &kOmniboxSourcesOptions);

bool AibOmniboxFilteringAllowsBookmarks() {
  const OmniboxSources sources = kAibOmniboxAutocompleteFilteringSources.Get();
  return sources == OmniboxSources::kSearchBookmarks ||
         sources == OmniboxSources::kSearchBookmarksChrome;
}

bool AibOmniboxFilteringAllowsBuiltinPages() {
  const OmniboxSources sources = kAibOmniboxAutocompleteFilteringSources.Get();
  return sources == OmniboxSources::kSearchChrome ||
         sources == OmniboxSources::kSearchBookmarksChrome;
}

}  // namespace aib::features
