# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.artifacts.tombstone_crashes import TombstoneCrashArtifact
from mvt.android.parsers.proto.tombstone import Tombstone

from ..utils import get_artifact


class TestTombstoneCrashArtifact:
    # def test_tombtone_process_parsing(self):
    #     tombstone_artifact = TombstoneCrashArtifact()
    #     file = get_artifact("android_data/tombstone_process.txt")
    #     with open(file, "rb") as f:
    #         data = f.read()

    #     tombstone_artifact.parse_text(data)
    #     assert len(tombstone_artifact.results) == 1

    # def test_tombtone_kernel_parsing(self):
    #     tombstone_artifact = TombstoneCrashArtifact()
    #     file = get_artifact("android_data/tombstone_kernel.txt")
    #     with open(file, "rb") as f:
    #         data = f.read()

    #     tombstone_artifact.parse_text(data)
    #     assert len(tombstone_artifact.results) == 1

    def test_tombstone_pb_process_parsing(self):
        file = get_artifact("android_data/tombstone_process.pb")
        with open(file, "rb") as f:
            data = f.read()

        parsed_tombstone = Tombstone().parse(data)
        assert parsed_tombstone
        assert parsed_tombstone.command_line == ["/vendor/bin/hw/android.hardware.media.c2@1.2-mediatek"]
        assert parsed_tombstone.uid == 1046
        assert parsed_tombstone.timestamp == "2023-04-12 12:32:40.518290770+0200"
