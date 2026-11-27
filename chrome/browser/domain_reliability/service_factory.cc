// Copyright 2014 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/domain_reliability/service_factory.h"

namespace domain_reliability {

const char kUploadReporterString[] = "chrome";

bool ShouldCreateService(const DomainReliabilityServiceDelegate* delegate) {
  // AI Browser: Domain Reliability (network-error beacons to Google
  // collectors) is never enabled, whatever the switches, policy or field
  // trials say.
  return false;
}

}  // namespace domain_reliability
