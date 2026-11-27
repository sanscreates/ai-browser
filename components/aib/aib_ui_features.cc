// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "components/aib/aib_ui_features.h"

#include "base/command_line.h"

namespace aib::features {

BASE_FEATURE(kAibPopupsToTabs, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibKeepWindowWithLastTab, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibScrollTabs, base::FEATURE_DISABLED_BY_DEFAULT);
constexpr base::FeatureParam<ScrollTabsMode>::Option kScrollTabsModeOptions[] =
    {
        {ScrollTabsMode::kAlways, "always"},
        {ScrollTabsMode::kNever, "never"},
};
BASE_FEATURE_ENUM_PARAM(ScrollTabsMode,
                        kAibScrollTabsMode,
                        &kAibScrollTabs,
                        "mode",
                        ScrollTabsMode::kAlways,
                        &kScrollTabsModeOptions);

bool ScrollEventChangesTab(bool platform_default) {
  if (!base::FeatureList::IsEnabled(kAibScrollTabs)) {
    return platform_default;
  }
  return kAibScrollTabsMode.Get() == ScrollTabsMode::kAlways;
}

BASE_FEATURE(kAibShowAvatarButton, base::FEATURE_DISABLED_BY_DEFAULT);
constexpr base::FeatureParam<AvatarButtonMode>::Option
    kAvatarButtonModeOptions[] = {
        {AvatarButtonMode::kAlways, "always"},
        {AvatarButtonMode::kIncognitoAndGuest, "incognito-and-guest"},
        {AvatarButtonMode::kNever, "never"},
};
BASE_FEATURE_ENUM_PARAM(AvatarButtonMode,
                        kAibShowAvatarButtonMode,
                        &kAibShowAvatarButton,
                        "mode",
                        AvatarButtonMode::kAlways,
                        &kAvatarButtonModeOptions);

BASE_FEATURE(kAibHideCrashedBubble, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibTabHoverCards, base::FEATURE_DISABLED_BY_DEFAULT);
constexpr base::FeatureParam<TabHoverCardsMode>::Option
    kTabHoverCardsModeOptions[] = {
        {TabHoverCardsMode::kNone, "none"},
        {TabHoverCardsMode::kTooltip, "tooltip"},
};
BASE_FEATURE_ENUM_PARAM(TabHoverCardsMode,
                        kAibTabHoverCardsMode,
                        &kAibTabHoverCards,
                        "mode",
                        TabHoverCardsMode::kNone,
                        &kTabHoverCardsModeOptions);

bool AreTabHoverCardsEnabled() {
  return !base::FeatureList::IsEnabled(kAibTabHoverCards);
}

bool ShouldShowTabTooltips() {
  return base::FeatureList::IsEnabled(kAibTabHoverCards) &&
         kAibTabHoverCardsMode.Get() == TabHoverCardsMode::kTooltip;
}

BASE_FEATURE(kAibHideTabCloseButtons, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibRemoveTabStripGrabHandle, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibHideBookmarkBarOnNtp, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibHideExtensionsMenu, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibHideFullscreenExitUi, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibCloseConfirmation, base::FEATURE_DISABLED_BY_DEFAULT);
constexpr base::FeatureParam<CloseConfirmationMode>::Option
    kCloseConfirmationModeOptions[] = {
        {CloseConfirmationMode::kLastWindow, "last-window"},
        {CloseConfirmationMode::kMultipleWindows, "multiple-windows"},
};
BASE_FEATURE_ENUM_PARAM(CloseConfirmationMode,
                        kAibCloseConfirmationMode,
                        &kAibCloseConfirmation,
                        "mode",
                        CloseConfirmationMode::kLastWindow,
                        &kCloseConfirmationModeOptions);

BASE_FEATURE(kAibIncognitoThemes, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibCustomNtpUrl, base::FEATURE_DISABLED_BY_DEFAULT);
BASE_FEATURE_PARAM(std::string,
                   kAibCustomNtpUrlParam,
                   &kAibCustomNtpUrl,
                   "url",
                   "");

const char kAibCustomNtpUrlSwitch[] = "aib-custom-ntp-url";

std::string GetCustomNewTabPageUrl() {
  const base::CommandLine* command_line =
      base::CommandLine::ForCurrentProcess();
  if (command_line->HasSwitch(kAibCustomNtpUrlSwitch)) {
    return command_line->GetSwitchValueASCII(kAibCustomNtpUrlSwitch);
  }
  if (!base::FeatureList::IsEnabled(kAibCustomNtpUrl)) {
    return std::string();
  }
  return kAibCustomNtpUrlParam.Get();
}

}  // namespace aib::features
