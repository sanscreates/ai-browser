// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "third_party/blink/public/common/aib_features.h"

#include "base/rand_util.h"
#include "base/unguessable_token.h"

namespace blink {
namespace features {

BASE_FEATURE(kAibCanvasImageDataNoise, base::FEATURE_ENABLED_BY_DEFAULT);

BASE_FEATURE(kAibClientRectsNoise, base::FEATURE_ENABLED_BY_DEFAULT);

BASE_FEATURE(kAibDisableLinkDrag, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibMeasureTextNoise, base::FEATURE_ENABLED_BY_DEFAULT);

BASE_FEATURE(kAibReducedSystemInfo, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibRemoveClientHints, base::FEATURE_DISABLED_BY_DEFAULT);

BASE_FEATURE(kAibSpoofWebGLInfo, base::FEATURE_DISABLED_BY_DEFAULT);
const base::FeatureParam<std::string> kAibSpoofWebGLInfoVendor{
    &kAibSpoofWebGLInfo, "vendor", ""};
const base::FeatureParam<std::string> kAibSpoofWebGLInfoRenderer{
    &kAibSpoofWebGLInfo, "renderer", ""};

}  // namespace features

uint64_t AibProcessNoiseSeed() {
  static const uint64_t seed = base::RandUint64();
  return seed;
}

double AibGeometryNoiseFactor(const base::UnguessableToken& token) {
  const uint64_t hash = base::UnguessableTokenHash()(token);
  // Offset of 5e-7 to 1e-6 (1000 steps), so the result stays distinct from
  // 1.0 even after rounding to float. The lowest bit picks the sign.
  const double offset = 5e-7 + static_cast<double>((hash >> 1) % 1000u) * 5e-10;
  return (hash & 1u) ? 1.0 + offset : 1.0 - offset;
}

}  // namespace blink
