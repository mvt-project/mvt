# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import re
from typing import AnyStr

from mvt.common.artifact import Artifact


class AndroidArtifact(Artifact):
    @staticmethod
    def extract_dumpsys_section(
        dumpsys: AnyStr, separator: AnyStr, binary=False
    ) -> AnyStr:
        """
        Extract a section from a full dumpsys file.

        :param dumpsys: content of the full dumpsys file (AnyStr)
        :param separator: content of the first line separator (AnyStr)
        :param binary: whether the dumpsys should be pared as binary or not (bool)
        :return: section extracted (string or bytes)
        """
        lines = []
        in_section = False
        delimiter = "------------------------------------------------------------------------------"
        if binary:
            delimiter = delimiter.encode("utf-8")

        for line in dumpsys.splitlines():
            if line.strip() == separator:
                in_section = True
                continue

            if not in_section:
                continue

            if line.strip().startswith(delimiter):
                break

            lines.append(line)

        return b"\n".join(lines) if binary else "\n".join(lines)
