# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import os
import datetime

import pytest

from mvt.android.artifacts.tombstone_crashes import TombstoneCrashArtifact

from ..utils import get_artifact


class TestTombstoneCrashArtifact:
    def test_tombtone_process_parsing(self):
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = "android_data/tombstone_process.txt"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        # Pass the file name and timestamp to the parse method
        file_name = os.path.basename(artifact_path)
        file_timestamp = datetime.datetime(2023, 4, 12, 12, 32, 40, 518290)
        tombstone_artifact.parse(file_name, file_timestamp, data)

        assert len(tombstone_artifact.results) == 1
        self.validate_tombstone_result(tombstone_artifact.results[0])

    def test_tombstone_pb_process_parsing(self):
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = "android_data/tombstone_process.pb"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        file_name = os.path.basename(artifact_path)
        file_timestamp = datetime.datetime(2023, 4, 12, 12, 32, 40, 518290)
        tombstone_artifact.parse_protobuf(file_name, file_timestamp, data)

        assert len(tombstone_artifact.results) == 1
        self.validate_tombstone_result(tombstone_artifact.results[0])

    @pytest.mark.skip(reason="Not implemented yet")
    def test_tombtone_kernel_parsing(self):
        tombstone_artifact = TombstoneCrashArtifact()
        file = get_artifact("android_data/tombstone_kernel.txt")
        with open(file, "rb") as f:
            data = f.read()

        tombstone_artifact.parse_text(data)
        assert len(tombstone_artifact.results) == 1

    def validate_tombstone_result(self, tombstone_result: dict):
        assert tombstone_result.get("command_line") == [
            "/vendor/bin/hw/android.hardware.media.c2@1.2-mediatek"
        ]
        assert tombstone_result.get("uid") == 1046
        assert tombstone_result.get("pid") == 25541
        assert tombstone_result.get("process_name") == "mtk.ape.decoder"

        # Check if the timestamp is correctly parsed, and converted to UTC
        # Original is in +0200: 2023-04-12 12:32:40.518290770+0200, result should be 2023-04-12 10:32:40.000000+0000
        assert tombstone_result.get("timestamp") == "2023-04-12 10:32:40.000000"
