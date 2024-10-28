# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.artifacts.tombstone_crashes import TombstoneCrashArtifact

from ..utils import get_artifact


class TestTombstoneCrashArtifact:
    def test_tombtone_process_parsing(self):
        tombstone_artifact = TombstoneCrashArtifact()
        file = get_artifact("android_data/tombstone_process.txt")
        with open(file, "rb") as f:
            data = f.read()

        tombstone_artifact.parse(data)

        assert len(tombstone_artifact.results) == 1

    def test_tombtone_kernel_parsing(self):
        tombstone_artifact = TombstoneCrashArtifact()
        file = get_artifact("android_data/tombstone_kernel.txt")
        with open(file, "rb") as f:
            data = f.read()

        tombstone_artifact.parse(data)

        assert len(tombstone_artifact.results) == 1
