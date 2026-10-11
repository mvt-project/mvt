# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_receivers import DumpsysReceiversArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysReceiversArtifact:
    def test_parsing(self):
        dr = DumpsysReceiversArtifact()
        file = get_artifact("android_data/dumpsys_packages.txt")
        with open(file) as f:
            data = f.read()

        assert len(dr.results) == 0
        dr.parse(data)
        assert len(dr.results) == 9
        assert dr.results[0]["resolver_type"] == "full_mime_type"
        storage_manager = next(
            result
            for result in dr.results
            if result["key"] == "com.android.storagemanager.automatic.SHOW_NOTIFICATION"
        )
        assert storage_manager["package_name"] == "com.android.storagemanager"

    def test_parsing_misindented_action(self):
        dr = DumpsysReceiversArtifact()
        data = """\
Receiver Resolver Table:
  Non-Data Actions:
      android.app.action.ENTER_CAR_MODE:
        b5b40f6 com.google.android.projection.gearhead/.CarModeBroadcastReceiver
               android.intent.action.MY_PACKAGE_REPLACED:
        e7706c1 com.psycatgames.nhiegame/.ScheduledNotificationBootReceiver
"""

        dr.parse(data)

        assert dr.results[1]["key"] == "android.intent.action.MY_PACKAGE_REPLACED"
        assert dr.results[1]["package_name"] == "com.psycatgames.nhiegame"

    def test_parsing_misindented_first_action(self):
        dr = DumpsysReceiversArtifact()
        data = """\
Receiver Resolver Table:
  Non-Data Actions:
               android.intent.action.MY_PACKAGE_REPLACED:
        e7706c1 com.psycatgames.nhiegame/.ScheduledNotificationBootReceiver
"""

        dr.parse(data)

        assert dr.results[0]["key"] == "android.intent.action.MY_PACKAGE_REPLACED"
        assert dr.results[0]["package_name"] == "com.psycatgames.nhiegame"

    def test_ioc_check(self, indicator_file):
        dr = DumpsysReceiversArtifact()
        file = get_artifact("android_data/dumpsys_packages.txt")
        with open(file) as f:
            data = f.read()
        dr.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.android.storagemanager")
        dr.indicators = ind
        assert len(dr.alertstore.alerts) == 0
        dr.check_indicators()
        assert len(dr.alertstore.alerts) == 1
