# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
from mvt.android.artifacts.artifact import AndroidArtifact

from ..utils import get_artifact


class TestAndroidArtifact:
    def test_extract_dumpsys_section(self):
        file = get_artifact("androidqf/dumpsys.txt")
        with open(file) as f:
            data = f.read()

        section = AndroidArtifact.extract_dumpsys_section(
            data, "DUMP OF SERVICE package:"
        )
        assert isinstance(section, str)
        assert len(section) == 3907
