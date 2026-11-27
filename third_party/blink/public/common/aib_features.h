// Copyright 2026 The AI Browser Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// AI Browser: anti-fingerprinting and privacy features. Each one is a plain
// base::Feature so it can be toggled from chrome://flags; the browser forwards
// the state to renderers through --enable-features/--disable-features.

#ifndef THIRD_PARTY_BLINK_PUBLIC_COMMON_AIB_FEATURES_H_
#define THIRD_PARTY_BLINK_PUBLIC_COMMON_AIB_FEATURES_H_

#include <stdint.h>

#include <string>

#include "base/feature_list.h"
#include "base/metrics/field_trial_params.h"
#include "third_party/blink/public/common/common_export.h"

namespace base {
class UnguessableToken;
}  // namespace base

namespace blink {
namespace features {

// Perturbs a few pixels of canvas readbacks (getImageData, toDataURL, toBlob,
// OffscreenCanvas.convertToBlob) so canvas fingerprints change per session.
BLINK_COMMON_EXPORT BASE_DECLARE_FEATURE(kAibCanvasImageDataNoise);

// Scales Element and Range client rects by a tiny per-document factor.
BLINK_COMMON_EXPORT BASE_DECLARE_FEATURE(kAibClientRectsNoise);

// Prevents links and selected text from being dragged.
BLINK_COMMON_EXPORT BASE_DECLARE_FEATURE(kAibDisableLinkDrag);

// Scales canvas measureText() results by a tiny per-context factor.
BLINK_COMMON_EXPORT BASE_DECLARE_FEATURE(kAibMeasureTextNoise);

// Reports a fixed low navigator.hardwareConcurrency and only low-entropy
// user-agent data.
BLINK_COMMON_EXPORT BASE_DECLARE_FEATURE(kAibReducedSystemInfo);

// Sends no user-agent client hints and leaves navigator.userAgentData empty.
BLINK_COMMON_EXPORT BASE_DECLARE_FEATURE(kAibRemoveClientHints);

// Replaces the WEBGL_debug_renderer_info unmasked vendor/renderer strings.
// Empty params mean the generic values WebGL already reports when masked.
BLINK_COMMON_EXPORT BASE_DECLARE_FEATURE(kAibSpoofWebGLInfo);
BLINK_COMMON_EXPORT extern const base::FeatureParam<std::string>
    kAibSpoofWebGLInfoVendor;
BLINK_COMMON_EXPORT extern const base::FeatureParam<std::string>
    kAibSpoofWebGLInfoRenderer;

}  // namespace features

// AI Browser: random value chosen once per process. Used as the seed for
// readback noise so results stay stable within a session but differ between
// sessions (and between renderer processes, i.e. between sites).
BLINK_COMMON_EXPORT uint64_t AibProcessNoiseSeed();

// AI Browser: maps a random token (e.g. a document token) to a multiplier
// that differs from 1.0 by between 5e-7 and 1e-6. The same token always gives
// the same factor.
BLINK_COMMON_EXPORT double AibGeometryNoiseFactor(
    const base::UnguessableToken& token);

}  // namespace blink

#endif  // THIRD_PARTY_BLINK_PUBLIC_COMMON_AIB_FEATURES_H_
