# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import logging

from mvt.android.parsers.backup import parse_backup_file, parse_tar_for_sms

from ..utils import get_artifact


class TestBackupParsing:
    def test_parsing_noencryption(self):
        file = get_artifact("android_backup/backup.ab")
        with open(file, "rb") as f:
            data = f.read()
        ddata = parse_backup_file(data)

        m = hashlib.sha256()
        m.update(ddata)
        assert m.hexdigest() == "0799b583788908f06bccb854608cede375041ee878722703a39182edeb008324"
        sms = parse_tar_for_sms(ddata)
        assert isinstance(sms, list)
        assert len(sms) == 1
        assert len(sms[0]["links"]) == 1
        assert sms[0]["links"][0] == "https://google.com/"

    def test_parsing_encryption(self):
        file = get_artifact("android_backup/backup2.ab")
        with open(file, "rb") as f:
            data = f.read()
        ddata = parse_backup_file(data, password="123456")

        m = hashlib.sha256()
        m.update(ddata)
        assert m.hexdigest() == "f365ace1effbc4902c6aeba241ca61544f8a96ad456c1861808ea87b7dd03896"
        sms = parse_tar_for_sms(ddata)
        assert isinstance(sms, list)
        assert len(sms) == 1
        assert len(sms[0]["links"]) == 1
        assert sms[0]["links"][0] == "https://google.com/"

    def test_parsing_compression(self):
        file = get_artifact("android_backup/backup3.ab")
        with open(file, "rb") as f:
            data = f.read()
        ddata = parse_backup_file(data)

        m = hashlib.sha256()
        m.update(ddata)
        assert m.hexdigest() == "33e73df2ede9798dcb3a85c06200ee41c8f52dd2f2e50ffafcceb0407bc13e3a"
        sms = parse_tar_for_sms(ddata)
        assert isinstance(sms, list)
        assert len(sms) == 1
        assert len(sms[0]["links"]) == 1
        assert sms[0]["links"][0] == "https://google.com/"
