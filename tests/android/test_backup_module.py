# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import json
import logging
import os
import tarfile
import zlib

import pytest

from mvt.android.modules.backup.sms import SMS
from mvt.android.parsers.backup import parse_backup_file
from mvt.common.config import settings
from mvt.common.module import run_module

from ..utils import get_android_backup_folder


class TestBackupModule:
    @pytest.mark.parametrize("link_fields", [{}, {"links": None}, {"links": []}])
    def test_collect_urls_with_empty_links(self, link_fields):
        mod = SMS()
        mod.results = [
            {"links": ["https://example.org/first"], "isodate": "2026-11-04 12:00:00"},
            {"body": "", **link_fields},
            {"links": ["https://example.org/last"], "isodate": "2026-11-04 13:00:00"},
        ]

        mod.collect_url_results()

        assert mod.url_results == [
            {
                "url": "https://example.org/first",
                "expanded_url": None,
                "timestamp": "2026-11-04 12:00:00",
                "source": "sms",
            },
            {
                "url": "https://example.org/last",
                "expanded_url": None,
                "timestamp": "2026-11-04 13:00:00",
                "source": "sms",
            },
        ]

    @pytest.mark.parametrize("message_type", ["sms", "mms"])
    @pytest.mark.parametrize("with_indicators", [False, True])
    def test_blank_message_backup(
        self,
        tmp_path,
        caplog,
        monkeypatch,
        indicators_factory,
        message_type,
        with_indicators,
    ):
        monkeypatch.setattr(settings, "NETWORK_ACCESS_ALLOWED", False)
        backup_path = tmp_path / "backup"
        relative_path = (
            f"apps/com.android.providers.telephony/d_f/000000_{message_type}_backup"
        )
        message_file = backup_path / relative_path
        message_file.parent.mkdir(parents=True)
        body_key = "body" if message_type == "sms" else "mms_body"
        messages = [
            {
                body_key: body,
                "date": str(1735689600000 + index * 1000),
                "date_sent": "0",
            }
            for index, body in enumerate(
                [
                    "",
                    "https://suspicious.example.org/first",
                    "ordinary message",
                    " \t ",
                    "",
                    "https://suspicious.example.org/last",
                ]
            )
        ]
        message_file.write_bytes(zlib.compress(json.dumps(messages).encode()))
        results_path = tmp_path / "results"
        results_path.mkdir()
        mod = SMS(target_path=str(backup_path), results_path=str(results_path))
        mod.from_dir(str(backup_path), [relative_path])
        if with_indicators:
            mod.indicators = indicators_factory(domains=["suspicious.example.org"])

        with caplog.at_level(logging.ERROR):
            run_module(mod)

        assert not [
            record for record in caplog.records if record.levelno == logging.ERROR
        ]
        assert len(mod.results) == len(messages)
        assert mod.results[0]["links"] is None
        assert mod.url_results == [
            {
                "url": f"https://suspicious.example.org/{suffix}",
                "expanded_url": None,
                "timestamp": mod.results[index]["isodate"],
                "source": "sms",
            }
            for index, suffix in [(1, "first"), (5, "last")]
        ]
        assert len(mod.alertstore.alerts) == (2 if with_indicators else 0)
        if with_indicators:
            assert [alert.event for alert in mod.alertstore.alerts] == [
                mod.results[1],
                mod.results[5],
            ]
        assert json.loads((results_path / "sms.json").read_text()) == mod.results

    def test_module_folder(self):
        backup_path = get_android_backup_folder()
        mod = SMS(target_path=backup_path)
        files = []
        for root, subdirs, subfiles in os.walk(os.path.abspath(backup_path)):
            for fname in subfiles:
                files.append(os.path.relpath(os.path.join(root, fname), backup_path))
        mod.from_dir(backup_path, files)
        run_module(mod)
        assert len(mod.results) == 2
        assert len(mod.results[0]["links"]) == 1
        assert mod.results[0]["links"][0] == "https://google.com/"

    def test_module_file(self):
        fpath = os.path.join(get_android_backup_folder(), "backup.ab")
        mod = SMS(target_path=fpath)
        with open(fpath, "rb") as f:
            data = f.read()
        tardata = parse_backup_file(data)
        dbytes = io.BytesIO(tardata)
        tar = tarfile.open(fileobj=dbytes)
        files = []
        for member in tar:
            files.append(member.name)
        mod.from_ab(fpath, tar, files)
        run_module(mod)
        assert len(mod.results) == 2
        assert len(mod.results[0]["links"]) == 1

    def test_module_file2(self):
        fpath = os.path.join(get_android_backup_folder(), "backup2.ab")
        mod = SMS(target_path=fpath)
        with open(fpath, "rb") as f:
            data = f.read()
        tardata = parse_backup_file(data, password="123456")
        dbytes = io.BytesIO(tardata)
        tar = tarfile.open(fileobj=dbytes)
        files = []
        for member in tar:
            files.append(member.name)
        mod.from_ab(fpath, tar, files)
        run_module(mod)
        assert len(mod.results) == 1
        assert len(mod.results[0]["links"]) == 1

    def test_module_file3(self):
        fpath = os.path.join(get_android_backup_folder(), "backup3.ab")
        mod = SMS(target_path=fpath)
        with open(fpath, "rb") as f:
            data = f.read()
        tardata = parse_backup_file(data)
        dbytes = io.BytesIO(tardata)
        tar = tarfile.open(fileobj=dbytes)
        files = []
        for member in tar:
            files.append(member.name)
        mod.from_ab(fpath, tar, files)
        run_module(mod)
        assert len(mod.results) == 1
        assert len(mod.results[0]["links"]) == 1
