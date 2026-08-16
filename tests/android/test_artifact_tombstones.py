# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import os
import datetime

import pytest

from mvt.android.artifacts.tombstone_crashes import TombstoneCrashArtifact
from mvt.android.parsers.proto.tombstone import Tombstone

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

    def test_text_tombstone_preserves_abort_message(self):
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = "android_data/bugreport/FS/data/tombstones/tombstone_00"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        tombstone_artifact.parse(
            os.path.basename(artifact_path),
            datetime.datetime(2021, 9, 29, 17, 43, 49),
            data,
        )

        assert tombstone_artifact.results[0]["abort_message"] == (
            "Check failed: payload.size() <= bytes_left "
            "(payload.size()=99, bytes_left=51) "
        )

    def test_protobuf_tombstone_preserves_abort_message_and_causes(self):
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = "android_data/tombstone_process.pb"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            tombstone = Tombstone().parse(f.read())

        tombstone.abort_message = "synthetic abort reason"
        tombstone_artifact.parse_protobuf(
            os.path.basename(artifact_path),
            datetime.datetime(2023, 4, 12, 12, 32, 40, 518290),
            bytes(tombstone),
        )

        result = tombstone_artifact.results[0]
        assert result["abort_message"] == "synthetic abort reason"
        assert result["causes"] == [
            {
                "human_readable": "null pointer dereference",
                "memory_error": None,
            }
        ]

    def test_text_tombstone_keeps_crashing_thread(self):
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = "android_data/tombstone_process.txt"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        data += (
            b"\npid: 25541, tid: 31896, name: worker-thread"
            b"  >>> /vendor/bin/other <<<\n"
        )
        tombstone_artifact.parse(
            os.path.basename(artifact_path),
            datetime.datetime(2023, 4, 12, 12, 32, 40, 518290),
            data,
        )

        result = tombstone_artifact.results[0]
        assert result["pid"] == 25541
        assert result["tid"] == 21307
        assert result["process_name"] == "mtk.ape.decoder"
        assert (
            result["binary_path"]
            == "/vendor/bin/hw/android.hardware.media.c2@1.2-mediatek"
        )

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

        # With Android logs we want to keep timestamps as device local time for consistency.
        # We often don't know the time offset for a log entry and so can't convert everything to UTC.
        # MVT should output the local time only:
        # So original 2023-04-12 12:32:40.518290770+0200 -> 2023-04-12 12:32:40.000000
        assert tombstone_result.get("timestamp") == "2023-04-12 12:32:40.518290"
