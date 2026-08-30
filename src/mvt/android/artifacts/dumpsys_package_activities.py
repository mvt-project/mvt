# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact
from .package_resolvers import parse_resolver_table


class DumpsysPackageActivitiesArtifact(AndroidArtifact):
    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for activity in self.results:
            ioc_match = self.indicators.check_app_id(activity["package_name"])
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", activity, matched_indicator=ioc_match.ioc
                )
                continue

    def parse(self, content: str) -> None:
        """
        Parse the Dumpsys Package section for activities
        Adds results to self.results

        :param content: content of the package section (string)
        """
        self.results = parse_resolver_table(content, "Activity")
