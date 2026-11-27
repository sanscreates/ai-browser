// Copyright 2014 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "third_party/blink/renderer/platform/graphics/static_bitmap_image.h"

#include <limits>
#include <optional>

#include "base/containers/span.h"
#include "base/numerics/checked_math.h"
#include "gpu/command_buffer/client/gles2_interface.h"
#include "skia/ext/skia_utils_base.h"
#include "third_party/blink/public/common/aib_features.h"
#include "third_party/blink/renderer/platform/graphics/accelerated_static_bitmap_image.h"
#include "third_party/blink/renderer/platform/graphics/graphics_context.h"
#include "third_party/blink/renderer/platform/graphics/image_observer.h"
#include "third_party/blink/renderer/platform/graphics/paint/paint_image.h"
#include "third_party/blink/renderer/platform/graphics/unaccelerated_static_bitmap_image.h"
#include "third_party/blink/renderer/platform/transforms/affine_transform.h"
#include "third_party/skia/include/core/SkCanvas.h"
#include "third_party/skia/include/core/SkData.h"
#include "third_party/skia/include/core/SkImage.h"
#include "third_party/skia/include/core/SkPaint.h"
#include "third_party/skia/include/core/SkPixmap.h"
#include "third_party/skia/include/core/SkSurface.h"
#include "ui/gfx/geometry/skia_conversions.h"
#include "ui/gfx/skia_span_util.h"
#include "v8/include/v8.h"

namespace blink {

namespace {

// AI Browser: on average one in this many visible pixels gets nudged.
constexpr uint64_t kAibReadbackNoiseRate = 128u;
constexpr size_t kAibBytesPerPixel = 4u;
// Index of the alpha byte in both RGBA and BGRA layouts.
constexpr size_t kAibAlphaIndex = 3u;

// AI Browser: bit mixer so that nearby inputs give unrelated outputs.
uint64_t AibMixBits(uint64_t value) {
  value ^= value >> 32;
  value *= 0xd6e8feb86659fd93ull;
  value ^= value >> 32;
  value *= 0xd6e8feb86659fd93ull;
  value ^= value >> 32;
  return value;
}

// AI Browser: moves one color channel of `pixel` by one step, staying within
// the valid range (for premultiplied data a channel can't exceed alpha).
void AibNudgePixel(base::span<uint8_t> pixel,
                   uint64_t hash,
                   bool premultiplied) {
  const size_t channel = static_cast<size_t>((hash >> 8) % kAibAlphaIndex);
  const int max_value = premultiplied ? pixel[kAibAlphaIndex] : 255;
  int value = pixel[channel];
  if (value >= max_value) {
    value -= 1;
  } else if (value == 0) {
    value += 1;
  } else {
    value += ((hash >> 16) & 1u) ? 1 : -1;
  }
  pixel[channel] = static_cast<uint8_t>(value);
}

}  // namespace

void AibAddReadbackNoise(const SkPixmap& pixmap) {
  const SkColorType color_type = pixmap.colorType();
  if ((color_type != kRGBA_8888_SkColorType &&
       color_type != kBGRA_8888_SkColorType) ||
      !pixmap.addr() || pixmap.width() <= 0 || pixmap.height() <= 0) {
    return;
  }
  const bool premultiplied = pixmap.alphaType() == kPremul_SkAlphaType;
  const uint64_t seed = AibProcessNoiseSeed();
  const base::span<uint8_t> bytes = gfx::SkPixmapToWritableSpan(pixmap);
  const size_t row_bytes = pixmap.rowBytes();
  const size_t width = static_cast<size_t>(pixmap.width());
  const size_t height = static_cast<size_t>(pixmap.height());

  // If the regular sampling picks nothing (tiny drawings), nudge the visible
  // pixel with the lowest hash instead so the output still changes.
  bool nudged_any = false;
  std::optional<size_t> fallback_offset;
  uint64_t fallback_hash = std::numeric_limits<uint64_t>::max();

  for (size_t y = 0; y < height; ++y) {
    for (size_t x = 0; x < width; ++x) {
      const size_t offset = y * row_bytes + x * kAibBytesPerPixel;
      base::span<uint8_t> pixel = bytes.subspan(offset, kAibBytesPerPixel);
      if (pixel[kAibAlphaIndex] == 0) {
        continue;
      }
      const uint64_t packed = static_cast<uint64_t>(pixel[0]) |
                              (static_cast<uint64_t>(pixel[1]) << 8) |
                              (static_cast<uint64_t>(pixel[2]) << 16) |
                              (static_cast<uint64_t>(pixel[3]) << 24);
      const uint64_t position = (static_cast<uint64_t>(y) << 32) | x;
      const uint64_t hash =
          AibMixBits(seed + AibMixBits(position) + AibMixBits(packed));
      if (hash % kAibReadbackNoiseRate == 0) {
        AibNudgePixel(pixel, hash, premultiplied);
        nudged_any = true;
      } else if (!nudged_any && hash < fallback_hash) {
        fallback_hash = hash;
        fallback_offset = offset;
      }
    }
  }

  if (!nudged_any && fallback_offset.has_value()) {
    AibNudgePixel(bytes.subspan(*fallback_offset, kAibBytesPerPixel),
                  fallback_hash, premultiplied);
  }
}

scoped_refptr<StaticBitmapImage> AibCopyWithReadbackNoise(
    scoped_refptr<StaticBitmapImage> image) {
  if (!image) {
    return image;
  }
  PaintImage paint_image = image->PaintImageForCurrentFrame();
  if (!paint_image || paint_image.IsPaintWorklet()) {
    return image;
  }
  const SkImageInfo info = paint_image.GetSkImageInfo();
  if (info.isEmpty() || (info.colorType() != kRGBA_8888_SkColorType &&
                         info.colorType() != kBGRA_8888_SkColorType)) {
    return image;
  }
  const size_t row_bytes = info.minRowBytes();
  const size_t size = info.computeByteSize(row_bytes);
  if (SkImageInfo::ByteSizeOverflowed(size)) {
    return image;
  }
  sk_sp<SkData> data = SkData::MakeZeroInitialized(size);
  const SkPixmap pixmap(info, data->writable_data(), row_bytes);
  if (!paint_image.readPixels(pixmap, 0, 0)) {
    return image;
  }
  AibAddReadbackNoise(pixmap);
  return StaticBitmapImage::Create(std::move(data), info,
                                   image->GetHdrMetadata(),
                                   image->Orientation());
}

scoped_refptr<StaticBitmapImage> StaticBitmapImage::Create(
    PaintImage image,
    ImageOrientation orientation) {
  DCHECK(!image.IsTextureBacked());
  return UnacceleratedStaticBitmapImage::Create(std::move(image), orientation);
}

scoped_refptr<StaticBitmapImage> StaticBitmapImage::Create(
    sk_sp<SkData> data,
    const SkImageInfo& info,
    const gfx::HDRMetadata& hdr_metadata,
    ImageOrientation orientation) {
  return UnacceleratedStaticBitmapImage::Create(
      SkImages::RasterFromData(info, std::move(data), info.minRowBytes()),
      orientation, hdr_metadata);
}

gfx::Size StaticBitmapImage::SizeWithConfig(SizeConfig config) const {
  gfx::Size size = GetSize();
  if (config.apply_orientation && orientation_.UsesWidthAsHeight())
    size.Transpose();
  return size;
}

Vector<uint8_t> StaticBitmapImage::CopyImageData(const SkImageInfo& info,
                                                 bool apply_orientation) {
  if (info.isEmpty())
    return {};
  PaintImage paint_image = PaintImageForCurrentFrame();
  if (paint_image.GetSkImageInfo().isEmpty())
    return {};

  wtf_size_t byte_length =
      base::checked_cast<wtf_size_t>(info.computeMinByteSize());
  if (byte_length > partition_alloc::MaxAllocationSize()) {
    return {};
  }
  Vector<uint8_t> dst_buffer(byte_length);
  const SkPixmap dst_pixmap =
      skia::MakeSkPixmap(info, dst_buffer, info.minRowBytes()).value();

  bool read_pixels_successful = paint_image.readPixels(dst_pixmap, 0, 0);
  DCHECK(read_pixels_successful);
  if (!read_pixels_successful)
    return {};

  // Orient the data, and re-read the pixels.
  if (apply_orientation && !HasDefaultOrientation()) {
    paint_image = Image::ResizeAndOrientImage(paint_image, Orientation(),
                                              gfx::Vector2dF(1, 1), 1,
                                              kInterpolationNone);
    read_pixels_successful = paint_image.readPixels(dst_pixmap, 0, 0);
    DCHECK(read_pixels_successful);
    if (!read_pixels_successful)
      return {};
  }

  return dst_buffer;
}

void StaticBitmapImage::DrawHelper(cc::PaintCanvas* canvas,
                                   const cc::PaintFlags& flags,
                                   const gfx::RectF& dst_rect,
                                   const gfx::RectF& src_rect,
                                   const ImageDrawOptions& draw_options,
                                   const PaintImage& image) {
  gfx::RectF adjusted_src_rect = src_rect;
  adjusted_src_rect.Intersect(gfx::RectF(image.width(), image.height()));

  if (dst_rect.IsEmpty() || adjusted_src_rect.IsEmpty())
    return;  // Nothing to draw.

  cc::PaintCanvasAutoRestore auto_restore(canvas, false);
  gfx::RectF adjusted_dst_rect = dst_rect;
  if (draw_options.respect_orientation &&
      orientation_ != ImageOrientationEnum::kDefault) {
    canvas->save();

    // ImageOrientation expects the origin to be at (0, 0)
    canvas->translate(adjusted_dst_rect.x(), adjusted_dst_rect.y());
    adjusted_dst_rect.set_origin(gfx::PointF());

    canvas->concat(
        orientation_.TransformFromDefault(adjusted_dst_rect.size()).ToSkM44());

    if (orientation_.UsesWidthAsHeight())
      adjusted_dst_rect.set_size(gfx::TransposeSize(adjusted_dst_rect.size()));
  }

  canvas->drawImageRect(image, gfx::RectFToSkRect(adjusted_src_rect),
                        gfx::RectFToSkRect(adjusted_dst_rect),
                        draw_options.sampling_options, &flags,
                        ToSkiaRectConstraint(draw_options.clamping_mode));
}

}  // namespace blink
