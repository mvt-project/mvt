# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from pathlib import Path

from mvt.common.module import run_module

from ..utils import get_android_androidqf, list_files


class TestAndroidqfMountsArtifact:
    def test_parse_mounts_token_checks(self):
        """
        Test the artifact-level `parse` method using tolerant token checks.

        Different parser variants may place mount tokens into different dict
        keys (for example `mount_options`, `pass_num`, `dump_freq`, etc.). To
        avoid brittle assertions we concatenate each parsed entry's values and
        look for expected tokens (device names, mount points, options) somewhere
        in the combined representation.
        """
        from mvt.android.artifacts.mounts import Mounts as MountsArtifact

        m = MountsArtifact()

        mount_lines = [
            "/dev/block/dm-12 on / type ext4 (ro,seclabel,noatime)",
            "/dev/block/by-name/system on /system type ext4 (rw,seclabel,noatime)",
            "/dev/block/by-name/data on /data type f2fs (rw,nosuid,nodev,noatime)",
        ]
        mount_content = "\n".join(mount_lines)

        # Parse the mount lines (artifact-level)
        m.parse(mount_content)

        # Basic sanity: parser should return one entry per input line
        assert len(m.results) == 3, f"Expected 3 parsed mounts, got: {m.results}"

        # Concatenate each entry's values into a single string so token checks
        # are tolerant to which dict keys were used by the parser.
        def concat_values(entry):
            parts = []
            for v in entry.values():
                try:
                    parts.append(str(v))
                except Exception:
                    # Skip values that can't be stringified
                    continue
            return " ".join(parts)

        concatenated = [concat_values(e) for e in m.results]

        # Token expectations (tolerant):
        # - Root line should include 'dm-12' and 'noatime' (and typically 'ro')
        assert any("dm-12" in s and "noatime" in s for s in concatenated), (
            f"No root-like tokens (dm-12 + noatime) found in parsed results: {concatenated}"
        )

        # - System line should include '/system' or 'by-name/system' and 'rw'
        assert any(
            (("by-name/system" in s or "/system" in s) and "rw" in s)
            for s in concatenated
        ), (
            f"No system-like tokens (system + rw) found in parsed results: {concatenated}"
        )

        # - Data line should include '/data' or 'by-name/data' and 'rw'
        assert any(
            (("by-name/data" in s or "/data" in s) and "rw" in s) for s in concatenated
        ), f"No data-like tokens (data + rw) found in parsed results: {concatenated}"


class TestAndroidqfMountsModule:
    def test_androidqf_module_no_mounts_file(self):
        """
        When no `mounts.json` is present in the androidqf dataset, the module
        should not produce results nor detections.
        """
        from mvt.android.modules.androidqf.mounts import Mounts

        data_path = get_android_androidqf()
        m = Mounts(target_path=data_path, log=logging)
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_folder(parent_path, files)

        run_module(m)

        # The provided androidqf test dataset does not include mounts.json, so
        # results should remain empty.
        assert len(m.results) == 0, (
            f"Expected no results when mounts.json is absent, got: {m.results}"
        )
        assert len(m.detected) == 0, f"Expected no detections, got: {m.detected}"
