# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import datetime
import os

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

        # With Android logs we want to keep timestamps as device local time for consistency.
        # We often don't know the time offset for a log entry and so can't convert everything to UTC.
        # MVT should output the local time only:
        # So original 2023-04-12 12:32:40.518290770+0200 -> 2023-04-12 12:32:40.000000
        assert tombstone_result.get("timestamp") == "2023-04-12 12:32:40.518290"

    def test_tombstone_pb_empty_timestamp(self):
        """Test parsing a protobuf tombstone with an empty timestamp."""
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = "android_data/bugreport_tombstones/tombstone_empty_timestamp.pb"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        file_name = os.path.basename(artifact_path)
        file_timestamp = datetime.datetime(2024, 1, 15, 10, 30, 45, 123456)
        tombstone_artifact.parse_protobuf(file_name, file_timestamp, data)

        assert len(tombstone_artifact.results) == 1
        result = tombstone_artifact.results[0]

        # When tombstone has empty timestamp, should use file modification time
        assert result.get("timestamp") == "2024-01-15 10:30:45.123456"
        assert result.get("pid") == 12345
        assert result.get("uid") == 1000
        assert result.get("signal_info", {}).get("name") == "SIGSEGV"

    def test_tombstone_pb_empty_timestamp_with_threads(self):
        """Test parsing a protobuf tombstone with empty timestamp and thread info."""
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = "android_data/bugreport_tombstones/tombstone_empty_timestamp_with_threads.pb"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        file_name = os.path.basename(artifact_path)
        file_timestamp = datetime.datetime(2024, 2, 20, 14, 15, 30, 0)
        tombstone_artifact.parse_protobuf(file_name, file_timestamp, data)

        assert len(tombstone_artifact.results) == 1
        result = tombstone_artifact.results[0]

        # Verify timestamp fallback
        assert result.get("timestamp") == "2024-02-20 14:15:30.000000"
        assert result.get("pid") == 9876
        assert result.get("uid") == 10001
        assert result.get("signal_info", {}).get("name") == "SIGABRT"
        assert result.get("process_name") == "ExampleThread"

    def test_tombstone_pb_whitespace_timestamp(self):
        """Test parsing a protobuf tombstone with whitespace-only timestamp."""
        tombstone_artifact = TombstoneCrashArtifact()
        artifact_path = (
            "android_data/bugreport_tombstones/tombstone_whitespace_timestamp.pb"
        )
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        file_name = os.path.basename(artifact_path)
        file_timestamp = datetime.datetime(2024, 3, 10, 8, 0, 0, 0)
        tombstone_artifact.parse_protobuf(file_name, file_timestamp, data)

        assert len(tombstone_artifact.results) == 1
        result = tombstone_artifact.results[0]

        # Verify whitespace timestamp is treated as empty
        assert result.get("timestamp") == "2024-03-10 08:00:00.000000"
        assert result.get("pid") == 11111
        assert result.get("uid") == 2000
        assert result.get("signal_info", {}).get("name") == "SIGILL"

    def test_tombstone_pb_empty_file(self):
        """Test that empty (0 bytes) tombstone files are handled gracefully."""
        artifact_path = "android_data/bugreport_tombstones/tombstone_empty_file.pb"
        file = get_artifact(artifact_path)
        with open(file, "rb") as f:
            data = f.read()

        # Verify the file is actually empty
        assert len(data) == 0, "Test file should be empty (0 bytes)"

        # Empty files should be skipped in the module (not parsed)
        # The actual skipping happens in the Tombstones module's run() method
        # This test verifies that empty data is detectable
