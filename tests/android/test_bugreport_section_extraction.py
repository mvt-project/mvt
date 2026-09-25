# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""A section ends at the next section, not at a timing line printed inside it."""

from mvt.android.modules.bugreport.base import BugReportModule

# dumpstate prints a section's duration when that section finishes, which can
# land in the middle of the section currently being written.
DUMPSTATE = """\
------ SYSTEM PROPERTIES (getprop) ------
[nfc.initialized]: [true]
------ 0.101s was the duration of 'DROPBOX SYSTEM SERVER CRASHES' ------
[ro.build.version.sdk]: [30]
[ro.product.model]: [SM-A305F]
------ 0.064s was the duration of 'SYSTEM PROPERTIES' ------
------ STORAGE INFO (df) ------
/dev/root  2.9G
"""


class TestExtractCommandSection:
    def test_a_foreign_timing_line_does_not_end_the_section(self):
        section = BugReportModule.extract_command_section(
            DUMPSTATE, "------ SYSTEM PROPERTIES"
        )
        assert "[ro.product.model]: [SM-A305F]" in section
        assert section.count("\n") == 2

    def test_the_next_section_is_still_the_boundary(self):
        section = BugReportModule.extract_command_section(
            DUMPSTATE, "------ SYSTEM PROPERTIES"
        )
        assert "STORAGE INFO" not in section
        assert "/dev/root" not in section

    def test_timing_lines_are_not_returned_as_content(self):
        section = BugReportModule.extract_command_section(
            DUMPSTATE, "------ SYSTEM PROPERTIES"
        )
        assert "was the duration of" not in section
