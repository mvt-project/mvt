# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import re

from .artifact import AndroidArtifact


# The AOSP dumpstate code is available at https://cs.android.com/android/platform/superproject/+/master:frameworks/native/cmds/dumpstate/
# The dumpstate code is used to generate bugreports on Android devices. It looks like there are
# bugs in the code that leave some sections with out ending lines. We need to handle these cases.
#
# The approach here is to flag probably broken section, and to search for plausible new section headers
# to close the previous section. This is a heuristic approach, and may not work in all cases. We can't do
# this for all sections as we will detect subsections as new sections.
SECTION_BROKEN_TERMINATORS = [
    b"VM TRACES AT LAST ANR"
]


class DumpStateArtifact(AndroidArtifact):
    def __init__(self, *args, **kwargs):
        self.dumpstate_sections = []
        self.dumpstate_header = {}
        self.unparsed_lines = []
        super().__init__(*args, **kwargs)

    def _parse_dumpstate_header(self, header_text):
        """
        Parse dumpstate header metadata
        """
        fields = {}
        for line in header_text.splitlines():
            if line.startswith(b"="):
                continue

            if b":" in line:
                # Save line if it's a key-value pair.
                key, value = line.split(b":", 1)
                fields[key] = value[1:]

            if not line and fields:
                # Finish if we get an empty line and already parsed lines
                break
            else:
                # Skip until we find lines
                continue

        self.dumpstate_header = fields
        return fields

    def _get_section_header(self, header_match):
        """
        Create internal dictionary to track dumpsys section.
        """
        section_full = header_match.group(0).strip(b"-").strip()
        section_name = header_match.group(1).rstrip()

        if header_match.group(2):
            section_command = header_match.group(2).strip(b"()")
        else:
            # Some headers can missed the command
            section_command = ""
            # import pdb; pdb.set_trace()

        has_broken_terminator = section_name in SECTION_BROKEN_TERMINATORS

        section = {
            "section_name": section_name,
            "section_command": section_command,
            "section_full": section_full,
            "missing_terminator": has_broken_terminator,
            "lines": [],
            "error": False,
        }
        self.dumpstate_sections.append(section)
        return section

    def parse_dumpstate(self, text: str) -> list:
        """
        Extract all sections from a full dumpstate file.

        :param text: content of the full dumpstate file (string)
        """
        # Parse the header
        self._parse_dumpstate_header(text)

        header = b"------ "

        # Regexes to parse headers
        section_name_re = re.compile(rb"------ ([\w\d\s\-\/\&]+)(\(.*\))? ------")
        missing_file_error_re = re.compile(rb"\*\*\* (.*): No such file or directory")
        generic_error_re = re.compile(rb"\*\*\* (.*)")

        section = None

        # Parse each line in dumpstate and look for headers
        for line in text.splitlines():
            if not section:
                possible_section_header = re.match(section_name_re, line)
                if possible_section_header:
                    section = self._get_section_header(possible_section_header)
                    # print("found section", section)
                    continue
                else:
                    # We continue to next line as we weren't already in a section
                    self.unparsed_lines.append(line)
                    continue

            if line.lstrip().startswith(header):
                # This may be an internal section, or the terminator for our current section
                # Ending looks like: ------ 0.557s was the duration of 'DUMPSYS CRITICAL' ------

                # Check that we have the end for the right command.
                section_command_in_quotes = b"'" + section["section_name"] + b"'"
                if (
                    section_command_in_quotes in line
                    or section["section_full"]
                    in line  # Needed for 0.070s was the duration of 'KERNEL LOG (dmesg)'
                ):
                    # Add end line and finish up the section
                    section["lines"].append(line)
                    section = None
                    continue

                # If we haven't closed previous, but this matches a section header, we can try close.
                # Probably a bug where not closed properly. We explicitly flag known broken fields.

                # This fails on these blocks if we dont blacklist. Maybe we need to make a blacklist of badly closed items
                # ------ DUMP BLOCK STAT ------
                # ------ BLOCK STAT (/sys/block/dm-20) ------

                possible_section_header = re.match(section_name_re, line)
                if possible_section_header and section["missing_terminator"]:
                    section = self._get_section_header(possible_section_header)
                else:
                    # Probably terminator for subsection, ignore and treat as a regular line.
                    pass

            # Handle lines with special meaning
            if re.match(missing_file_error_re, line) or  re.match(generic_error_re, line):
                # The line in a failed file read which is dumped without an header end section.
                section["failed"] = True
                section["lines"].append(line)
                section = None
            else:
                section["lines"].append(line)

        return self.dumpstate_sections
