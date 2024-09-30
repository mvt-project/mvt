# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
from mvt.android.artifacts.dumpstate_artifact import DumpStateArtifact

from ..utils import get_artifact


class TestAndroidArtifactDumpState:
    def _parse_dump_state(self):
        """
        Load the test artifact
        """
        file = get_artifact("android_data/bugreport/dumpstate.txt")
        with open(file, "rb") as f:
            data = f.read()
        dumpstate = DumpStateArtifact()
        dumpstate.parse_dumpstate(data)
        return dumpstate

    def test_extract_dumpstate_sections(self):
        """
        Test parsing of dumpstate sections
        """
        dumpstate = self._parse_dump_state()
        assert len(dumpstate.dumpstate_sections) == 4

        assert len(dumpstate.dumpstate_header) == 4
        assert dumpstate.dumpstate_header.get(b"Bugreport format version") == b"2.0"

        for section in dumpstate.dumpstate_sections:
            if section["section_name"] == b"SYSTEM LOG":
                assert len(section["lines"]) == 5
                assert section["lines"][0].startswith(b"--------- beginning of system")

            elif section["section_name"] == b"MODEM CRASH HISTORY":
                # Test parsing where section only has an error message
                assert len(section["lines"]) == 1
                assert section["lines"][0] == b"*** /data/tombstones//modem/mcrash_history: No such file or directory"

        assert len(dumpstate.unparsed_lines) == 10