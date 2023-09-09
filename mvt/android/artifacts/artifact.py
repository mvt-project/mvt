# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.artifact import Artifact


class AndroidArtifact(Artifact):
    @staticmethod
    def extract_dumpsys_section(dumpsys: str, separator: str) -> str:
        """
        Extract a section from a full dumpsys file.

        :param dumpsys: content of the full dumpsys file (string)
        :param separator: content of the first line separator (string)
        :return: section extracted (string)
        """
        lines = []
        in_section = False
        for line in dumpsys.splitlines():
            if line.strip() == separator:
                in_section = True
                continue

            if not in_section:
                continue

            if line.strip().startswith(
                "------------------------------------------------------------------------------"
            ):
                break

            lines.append(line)

        return "\n".join(lines)
