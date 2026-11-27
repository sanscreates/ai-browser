// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef COMPONENTS_AIB_AIB_UI_FEATURES_H_
#define COMPONENTS_AIB_AIB_UI_FEATURES_H_

#include <string>

#include "base/feature_list.h"
#include "base/metrics/field_trial_params.h"
#include "components/aib/aib_features_export.h"

// AI Browser's optional browser UI behaviors. Every feature here is disabled
// by default, and the disabled state is stock Chromium behavior.
namespace aib::features {

// Pages that call window.open() as a popup get a foreground tab instead of a
// popup window.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibPopupsToTabs);

// Closing the last tab of a normal window opens a New Tab page in its place
// instead of closing the window. Closing the window itself still works.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibKeepWindowWithLastTab);

// Overrides whether a mouse wheel over the tab strip switches tabs.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibScrollTabs);
enum class ScrollTabsMode {
  kAlways,
  kNever,
};
// Param "mode": "always" (default) or "never".
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE_PARAM(ScrollTabsMode,
                                               kAibScrollTabsMode);
// Returns whether wheel scrolling over the tab strip should switch tabs, given
// the platform default.
AIB_FEATURES_EXPORT bool ScrollEventChangesTab(bool platform_default);

// Overrides when the profile (avatar) toolbar button is shown.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibShowAvatarButton);
enum class AvatarButtonMode {
  kAlways,
  kIncognitoAndGuest,
  kNever,
};
// Param "mode": "always" (default), "incognito-and-guest" or "never".
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE_PARAM(AvatarButtonMode,
                                               kAibShowAvatarButtonMode);

// Never shows the "Restore pages?" bubble after an unclean exit.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibHideCrashedBubble);

// Replaces tab hover cards with nothing or with a plain tooltip.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibTabHoverCards);
enum class TabHoverCardsMode {
  kNone,
  kTooltip,
};
// Param "mode": "none" (default) or "tooltip".
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE_PARAM(TabHoverCardsMode,
                                               kAibTabHoverCardsMode);
// Returns whether tab hover cards may be shown at all.
AIB_FEATURES_EXPORT bool AreTabHoverCardsEnabled();
// Returns whether tabs should show their title as a tooltip instead.
AIB_FEATURES_EXPORT bool ShouldShowTabTooltips();

// Hides the close button on tabs.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibHideTabCloseButtons);

// Removes the empty window-drag area that is reserved at the end of the tab
// strip.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibRemoveTabStripGrabHandle);

// The bookmark bar never shows itself automatically on the New Tab page. The
// user's "always show bookmarks bar" choice still applies.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibHideBookmarkBarOnNtp);

// Hides the extensions (puzzle piece) button and pinned extension actions.
// The container still appears briefly when an extension popup or the
// extensions menu needs an anchor.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibHideExtensionsMenu);

// Hides the "Press Esc to exit full screen" bubble and the fullscreen exit
// button.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibHideFullscreenExitUi);

// Asks for confirmation before closing a window that has several tabs.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibCloseConfirmation);
enum class CloseConfirmationMode {
  // Only when closing the last open window.
  kLastWindow,
  // For every window, including while other windows stay open.
  kMultipleWindows,
};
// Param "mode": "last-window" (default) or "multiple-windows".
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE_PARAM(CloseConfirmationMode,
                                               kAibCloseConfirmationMode);

// Lets the profile's browser theme apply to Incognito windows too.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibIncognitoThemes);

// Opens a custom URL as the New Tab page.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE(kAibCustomNtpUrl);
// Param "url": the page to open. Empty means no override.
AIB_FEATURES_EXPORT BASE_DECLARE_FEATURE_PARAM(std::string,
                                               kAibCustomNtpUrlParam);
// Command-line switch that also sets the custom New Tab page, so the URL can
// be typed into a chrome://flags text box. It takes precedence over the
// feature param.
AIB_FEATURES_EXPORT extern const char kAibCustomNtpUrlSwitch[];
// Returns the custom New Tab page URL as typed by the user (not validated), or
// an empty string if none is set.
AIB_FEATURES_EXPORT std::string GetCustomNewTabPageUrl();

}  // namespace aib::features

#endif  // COMPONENTS_AIB_AIB_UI_FEATURES_H_
