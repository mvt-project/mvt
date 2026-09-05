# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.artifacts.settings import Settings as SettingsArtifact

from .base import AndroidQFModule


class AQFSettings(SettingsArtifact, AndroidQFModule):
    """This module analyse setting files"""

    def run(self) -> None:
        for setting_file in self._get_files_by_pattern("*/settings_*.txt"):
            namespace = setting_file[setting_file.rfind("_") + 1 : -4]

            data = self._get_file_content(setting_file)
            for line in data.decode("utf-8").splitlines():
                name, separator, value = line.strip().partition("=")
                if not separator:
                    continue

                self.results.append(
                    {
                        "namespace": namespace,
                        "user": None,
                        "name": name,
                        "value": value,
                    }
                )

        self.log.info("Identified %d settings", len(self.results))
