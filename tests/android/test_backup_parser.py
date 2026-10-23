# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import json
import zlib

import pytest

from mvt.android.parsers.backup import (
    AndroidBackupParsingError,
    parse_ab_header,
    parse_backup_file,
    parse_sms_file,
    parse_tar_for_sms,
)

from ..utils import get_artifact


class TestBackupParsing:
    def test_parse_incomplete_header(self):
        assert parse_ab_header(b"ANDROID BACKUP\n") == {
            "backup": False,
            "compression": None,
            "version": None,
            "encryption": None,
        }

    def test_parse_truncated_encrypted_header(self):
        with pytest.raises(
            AndroidBackupParsingError, match="Invalid encrypted backup header"
        ):
            parse_backup_file(
                b"ANDROID BACKUP\n5\n0\nAES-256\ntruncated", password="password"
            )

    def test_parsing_noencryption(self):
        file = get_artifact("android_backup/backup.ab")
        with open(file, "rb") as f:
            data = f.read()
        ddata = parse_backup_file(data)

        m = hashlib.sha256()
        m.update(ddata)
        assert (
            m.hexdigest()
            == "ce1ac5009fea5187a9f546b51e1446ba450243ae91d31dc779233ec0937b5d18"
        )
        sms = parse_tar_for_sms(ddata)
        assert isinstance(sms, list)
        assert len(sms) == 2
        assert len(sms[0]["links"]) == 1
        assert sms[0]["links"][0] == "http://google.com"
        assert sms[0]["isodate"] == "2020-01-20 14:49:49.000000"
        assert sms[0]["direction"] == "received"
        assert sms[0]["date"] == "1579531789"
        assert sms[0]["date_sent"] == "1579531786"
        assert sms[0]["msg_box"] == "1"
        assert sms[1]["isodate"] == "2022-02-22 15:29:41.956000"
        assert sms[1]["direction"] == "sent"

    def test_parsing_encryption(self):
        file = get_artifact("android_backup/backup2.ab")
        with open(file, "rb") as f:
            data = f.read()
        ddata = parse_backup_file(data, password="123456")

        m = hashlib.sha256()
        m.update(ddata)
        assert (
            m.hexdigest()
            == "f365ace1effbc4902c6aeba241ca61544f8a96ad456c1861808ea87b7dd03896"
        )
        sms = parse_tar_for_sms(ddata)
        assert isinstance(sms, list)
        assert len(sms) == 1
        assert len(sms[0]["links"]) == 1
        assert sms[0]["links"][0] == "https://google.com/"
        assert sms[0]["isodate"] == "2022-02-22 15:29:41.956000"
        assert sms[0]["direction"] == "sent"

    def test_parsing_compression(self):
        file = get_artifact("android_backup/backup3.ab")
        with open(file, "rb") as f:
            data = f.read()
        ddata = parse_backup_file(data)

        m = hashlib.sha256()
        m.update(ddata)
        assert (
            m.hexdigest()
            == "33e73df2ede9798dcb3a85c06200ee41c8f52dd2f2e50ffafcceb0407bc13e3a"
        )
        sms = parse_tar_for_sms(ddata)
        assert isinstance(sms, list)
        assert len(sms) == 1
        assert len(sms[0]["links"]) == 1
        assert sms[0]["links"][0] == "https://google.com/"
        assert sms[0]["isodate"] == "2022-02-22 15:29:41.956000"
        assert sms[0]["direction"] == "sent"

    @pytest.mark.parametrize(
        "entry",
        [
            {"body": "Message", "type": "1", "date": "1451322716000"},
            {"mms_body": "Message", "msg_box": "1", "date": "1451322716"},
        ],
    )
    def test_sms_and_mms_timestamp_units(self, entry):
        data = zlib.compress(json.dumps([entry]).encode("utf-8"))

        message = parse_sms_file(data)[0]

        assert message["isodate"] == "2015-12-28 17:11:56.000000"
        assert message["date"] == entry["date"]
        assert message["body"] == "Message"
        # A timestamp is not required to infer a direction from the mailbox.
        assert message["direction"] == "received"
        assert "date_sent" not in message

    @pytest.mark.parametrize("date_sent", ["0", "1450893514000"])
    @pytest.mark.parametrize(
        ("message_type", "direction"),
        [
            ("1", "received"),
            (2, "sent"),
            ("4", "sent"),
            ("5", "sent"),
            ("6", "sent"),
            ("3", "unknown"),
            ("0", "unknown"),
            ("99", "unknown"),
            (None, "unknown"),
            ("unknown", "unknown"),
        ],
    )
    def test_sms_direction_uses_type(self, message_type, direction, date_sent):
        entry = {
            "body": "Message",
            "date": "1450893518140",
            "date_sent": date_sent,
        }
        if message_type is not None:
            entry["type"] = message_type
        data = zlib.compress(json.dumps([entry]).encode("utf-8"))

        message = parse_sms_file(data)[0]

        assert message["direction"] == direction
        assert message["date_sent"] == date_sent
        assert message.get("type") == message_type

    @pytest.mark.parametrize("date_sent", ["0", "1451322716"])
    @pytest.mark.parametrize(
        ("message_box", "direction"),
        [
            (1, "received"),
            ("2", "sent"),
            ("4", "sent"),
            ("5", "sent"),
            ("3", "unknown"),
            ("0", "unknown"),
            ("6", "unknown"),
            ("99", "unknown"),
            (None, "unknown"),
            ("unknown", "unknown"),
        ],
    )
    def test_mms_direction_uses_message_box(self, message_box, direction, date_sent):
        entry = {
            "mms_body": "Message",
            "date": "1451322716",
            "date_sent": date_sent,
            # MMS direction comes from msg_box, not an SMS type field.
            "type": "1",
        }
        if message_box is not None:
            entry["msg_box"] = message_box
        data = zlib.compress(json.dumps([entry]).encode("utf-8"))

        message = parse_sms_file(data)[0]

        assert message["direction"] == direction
        assert message["date_sent"] == date_sent
        assert message.get("msg_box") == message_box
