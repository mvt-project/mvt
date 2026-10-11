# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""A mount is writable only if both mountinfo option layers allow it."""

from mvt.android.artifacts.mounts import Mounts
from mvt.common.alerts import AlertLevel

# fields[5] is the per-mount (VFS) layer, the field after "-" the superblock.
RO_OVERLAY = (
    "304 166 0:130 / /product/usr rw,relatime shared:63 - overlay overlay "
    "ro,seclabel,lowerdir=/mnt/vendor/ext/product/usr:/product/usr"
)
RW_SYSTEM = (
    "305 166 0:131 / /system rw,relatime shared:64 - ext4 /dev/block/dm-1 "
    "rw,seclabel,errors=panic"
)


def _run(line):
    mounts = Mounts()
    mounts.results = Mounts.parse_mountinfo(line, 1)
    mounts.check_indicators()
    return mounts


class TestMountsReadWriteLayers:
    def test_rw_vfs_over_ro_superblock_is_not_writable(self):
        mounts = _run(RO_OVERLAY)
        assert mounts.results[0]["is_read_write"] is False
        assert mounts.alertstore.count(AlertLevel.HIGH) == 0
        assert mounts.alertstore.count(AlertLevel.MEDIUM) == 0

    def test_rw_in_both_layers_still_alerts(self):
        mounts = _run(RW_SYSTEM)
        assert mounts.results[0]["is_read_write"] is True
        assert mounts.alertstore.count(AlertLevel.HIGH) == 1

    def test_both_option_layers_are_still_reported(self):
        mounts = _run(RO_OVERLAY)
        options = mounts.results[0]["options_list"]
        assert "rw" in options and "ro" in options
