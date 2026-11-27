// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "extensions/common/aib_content_blocker.h"

#include <string>

#include "base/no_destructor.h"
#include "extensions/common/hashed_extension_id.h"

namespace extensions {

bool IsAibContentBlocker(std::string_view extension_id) {
  return extension_id == kAibContentBlockerExtensionId;
}

bool IsAibContentBlocker(const HashedExtensionId& hashed_id) {
  // Both hashes are always computed; compare the one that doesn't depend on
  // which of them value() currently returns.
  static const base::NoDestructor<std::string> kHash(
      HashedExtensionId(kAibContentBlockerExtensionId).value_sha256());
  return hashed_id.value_sha256() == *kHash;
}

}  // namespace extensions
