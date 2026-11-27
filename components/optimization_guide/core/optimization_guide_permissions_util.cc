// Copyright 2019 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "components/optimization_guide/core/optimization_guide_permissions_util.h"

#include <memory>

#include "base/command_line.h"
#include "components/unified_consent/url_keyed_data_collection_consent_helper.h"
#include "google_apis/google_api_keys.h"

namespace {

bool ShouldOverrideCheckingUserPermissionsToFetchHintsForTesting() {
  base::CommandLine* command_line = base::CommandLine::ForCurrentProcess();
  return command_line->HasSwitch(
      optimization_guide::kDisableCheckingUserPermissionsForTestingSwitch);
}

}  // namespace

namespace optimization_guide {

bool ShouldSkipGoogleApiKeyConfigurationCheck() {
  base::CommandLine* command_line = base::CommandLine::ForCurrentProcess();
  return command_line->HasSwitch(
      kGoogleApiKeyConfigurationCheckOverrideSwitch);
}

bool IsUserPermittedToFetchFromRemoteOptimizationGuide(
    bool is_off_the_record,
    PrefService* pref_service) {
  if (is_off_the_record)
    return false;

  if (ShouldOverrideCheckingUserPermissionsToFetchHintsForTesting()) {
    return true;
  }

  // AI Browser: never fetch hints or models from the remote Optimization
  // Guide service.
  return false;
}

}  // namespace optimization_guide
