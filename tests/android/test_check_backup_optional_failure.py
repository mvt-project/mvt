# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""An encrypted backup.ab must not take the whole check-androidqf run with it.

`CmdAndroidCheckBackup.from_ab()` already raises `InvalidAndroidBackup` instead
of exiting when it runs as a sub-command (`check-androidqf` catches that and
skips the backup modules), for a wrong file format and for a parse error. The
password branches used to call `sys.exit(1)` unconditionally, which ends the
parent run inside `finish()` — before the intrusion-logs command and before the
timeline, alerts, urls, info and run-manifest are written.
"""

import pytest

from mvt.android.cmd_check_backup import CmdAndroidCheckBackup, InvalidAndroidBackup

ENCRYPTED_AB_HEADER = b"ANDROID BACKUP\n5\n0\nAES-256\n" + b"\x00" * 64


class TestCheckBackupOptionalFailure:
    def _cmd(self, tmp_path, sub_command):
        return CmdAndroidCheckBackup(
            target_path=None,
            results_path=str(tmp_path),
            module_options={"interactive": False},
            sub_command=sub_command,
        )

    def test_missing_password_raises_when_nested(self, tmp_path):
        cmd = self._cmd(tmp_path, sub_command=True)
        with pytest.raises(InvalidAndroidBackup):
            cmd.from_ab(ENCRYPTED_AB_HEADER)

    def test_missing_password_still_exits_on_its_own_command(self, tmp_path):
        cmd = self._cmd(tmp_path, sub_command=False)
        with pytest.raises(SystemExit):
            cmd.from_ab(ENCRYPTED_AB_HEADER)
