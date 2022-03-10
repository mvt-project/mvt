# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import logging
import os
import tarfile

from mvt.android.modules.backup.sms import SMS
from mvt.android.parsers.backup import parse_backup_file
from mvt.common.module import run_module

from ..utils import get_android_backup_folder


class TestBackupModule:
    def test_module_folder(self):
        backup_path = get_android_backup_folder()
        mod = SMS(base_folder=backup_path, log=logging)
        files = []
        for root, subdirs, subfiles in os.walk(os.path.abspath(backup_path)):
            for fname in subfiles:
                files.append(os.path.relpath(os.path.join(root, fname), backup_path))
        mod.from_folder(backup_path, files)
        run_module(mod)
        assert len(mod.results) == 1
        assert len(mod.results[0]["links"]) == 1
        assert mod.results[0]["links"][0] == "https://google.com/"

    def test_module_file(self):
        fpath = os.path.join(get_android_backup_folder(), "backup.ab")
        mod = SMS(base_folder=fpath, log=logging)
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

    def test_module_file2(self):
        fpath = os.path.join(get_android_backup_folder(), "backup2.ab")
        mod = SMS(base_folder=fpath, log=logging)
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
        mod = SMS(base_folder=fpath, log=logging)
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
