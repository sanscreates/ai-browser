// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef EXTENSIONS_COMMON_AIB_CONTENT_BLOCKER_H_
#define EXTENSIONS_COMMON_AIB_CONTENT_BLOCKER_H_

#include <string_view>

namespace extensions {

class HashedExtensionId;

// AI Browser's built-in ad and tracker blocker is uBlock Origin, loaded as a
// component extension so that it can't be removed or disabled. It is
// third-party code, so it doesn't get the extra privileges Chromium gives its
// own component extensions (every extension API, scripting on any page,
// ignoring policy-blocked hosts): there it is treated like a regular
// extension.
inline constexpr char kAibContentBlockerExtensionId[] =
    "mfhbhkgdijnaendiokmdbdedghofepdf";

// Whether `extension_id` (or its hash) is the content blocker's.
bool IsAibContentBlocker(std::string_view extension_id);
bool IsAibContentBlocker(const HashedExtensionId& hashed_id);

}  // namespace extensions

#endif  // EXTENSIONS_COMMON_AIB_CONTENT_BLOCKER_H_
