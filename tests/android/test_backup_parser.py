# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib

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
        assert m.hexdigest() == "ce1ac5009fea5187a9f546b51e1446ba450243ae91d31dc779233ec0937b5d18"
        sms = parse_tar_for_sms(ddata)
        assert isinstance(sms, list)
        assert len(sms) == 2
        assert len(sms[0]["links"]) == 1
        assert sms[0]["links"][0] == "http://google.com"

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
