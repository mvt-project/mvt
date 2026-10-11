# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
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
        in_section = False
        delimiter_str = "------------------------------------------------------------------------------"
        delimiter_bytes = b"------------------------------------------------------------------------------"

        if binary:
            lines_bytes = []
            for line in dumpsys.splitlines():  # type: ignore[union-attr]
                if line.strip() == separator:  # type: ignore[arg-type]
                    in_section = True
                    continue

                if not in_section:
                    continue

                if line.strip().startswith(delimiter_bytes):  # type: ignore[arg-type]
                    break

                lines_bytes.append(line)  # type: ignore[arg-type]

            return b"\n".join(lines_bytes)  # type: ignore[return-value,arg-type]
        else:
            lines_str = []
            for line in dumpsys.splitlines():  # type: ignore[union-attr]
                if line.strip() == separator:  # type: ignore[arg-type]
                    in_section = True
                    continue

                if not in_section:
                    continue

                if line.strip().startswith(delimiter_str):  # type: ignore[arg-type]
                    break

                lines_str.append(line)  # type: ignore[arg-type]

            return "\n".join(lines_str)  # type: ignore[return-value,arg-type]
