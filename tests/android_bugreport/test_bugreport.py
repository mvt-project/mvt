# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

from mvt.android.modules.bugreport.base import BugReportModule
from mvt.android.modules.bugreport.dumpsys_appops import DumpsysAppops
from mvt.android.modules.bugreport.dumpsys_getprop import DumpsysGetProp
from mvt.android.modules.bugreport.dumpsys_packages import DumpsysPackages
from mvt.android.modules.bugreport.dumpsys_receivers import DumpsysReceivers
from mvt.android.modules.bugreport.tombstones import Tombstones
from mvt.common.module import run_module

from ..utils import get_artifact_folder


class TestBugreportAnalysis:
    def launch_bug_report_module(self, module):
        fpath = os.path.join(get_artifact_folder(), "android_data/bugreport/")
        m = module(target_path=fpath)
        folder_files = []
        parent_path = Path(fpath).absolute().as_posix()
        for root, subdirs, subfiles in os.walk(os.path.abspath(fpath)):
            for file_name in subfiles:
                folder_files.append(
                    os.path.relpath(os.path.join(root, file_name), parent_path)
                )
        m.from_dir(fpath, folder_files)
        run_module(m)
        return m

    def test_appops_module(self):
        m = self.launch_bug_report_module(DumpsysAppops)
        assert len(m.results) == 12
        assert len(m.timeline) == 16

        detected_by_ioc = [
            detected
            for detected in m.alertstore.alerts
            if detected.event.get("matched_indicator")
        ]
        assert (
            len(m.alertstore.alerts) == 1
        )  # Hueristic detection for suspicious permissions
        assert len(detected_by_ioc) == 0

    def test_packages_module(self):
        m = self.launch_bug_report_module(DumpsysPackages)
        assert len(m.results) == 2
        assert (
            m.results[0]["package_name"]
            == "com.samsung.android.provider.filterprovider"
        )
        assert m.results[1]["package_name"] == "com.instagram.android"
        assert len(m.results[0]["permissions"]) == 4
        assert len(m.results[1]["permissions"]) == 32

    def test_getprop_module(self):
        m = self.launch_bug_report_module(DumpsysGetProp)
        assert len(m.results) == 0

    def test_receivers_match_exact_package_name(self, indicators_factory):
        intent = "android.intent.action.PHONE_STATE"
        false_positive = {
            "package_name": "com.android.phone",
            "receiver": (
                "com.android.phone/"
                "com.android.services.telephony.sip.SipIncomingCallReceiver"
            ),
        }
        malicious_receiver = {
            "package_name": "com.android.services",
            "receiver": "com.android.services/com.example.SomeReceiver",
        }
        module = DumpsysReceivers(
            results={intent: [false_positive, malicious_receiver]}
        )
        module.indicators = indicators_factory(app_ids=["com.android.services"])

        module.check_indicators()

        assert len(module.alertstore.alerts) == 1
        alert = module.alertstore.alerts[0]
        assert alert.event == {intent: malicious_receiver}
        assert alert.matched_indicator.value == "com.android.services"

    def test_tombstones_modules(self):
        m = self.launch_bug_report_module(Tombstones)
        assert len(m.results) == 2
        assert m.results[1]["pid"] == 3559

    def test_dumpstate_section_is_cached_across_parallel_modules(self):
        dumpstate = (
            b"header\n"
            b"------ SYSTEM PROPERTIES (getprop) ------\n"
            b"[persist.sys.timezone]: [Europe/Berlin]\n"
            b"------------------------------------------------------------------------------\n"
            b"------\n"
            b"DUMP OF SERVICE package:\n"
            b"package data\n"
            b"------------------------------------------------------------------------------\n"
            b"DUMP OF SERVICE package:\n"
            b"duplicate package data\n"
            b"------------------------------------------------------------------------------\n"
            b"DUMP OF SERVICE adb:\n"
            b"adb data\n"
            b"------------------------------------------------------------------------------\n"
        )
        archive = MagicMock()
        archive.open.side_effect = lambda _: BytesIO(dumpstate)
        shared_lock = threading.RLock()
        shared_cache = {}
        modules = []

        for _ in range(4):
            module = BugReportModule()
            module.from_zip(archive, ["dumpState_test.log"])
            module.resource_lock = shared_lock
            module.resource_cache = shared_cache
            modules.append(module)

        with ThreadPoolExecutor(max_workers=4) as executor:
            sections = list(
                executor.map(
                    lambda module: module._get_dumpsys_section(
                        "DUMP OF SERVICE package:"
                    ),
                    modules,
                )
            )

        assert sections == ["package data"] * 4
        assert all(section is sections[0] for section in sections)
        assert modules[0]._get_dumpsys_section_bytes(b"DUMP OF SERVICE adb:") == (
            b"adb data"
        )
        assert modules[0]._get_system_properties_text() == (
            "[persist.sys.timezone]: [Europe/Berlin]"
        )
        archive.open.assert_called_once_with("dumpState_test.log")
