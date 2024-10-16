# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import plistlib
from base64 import b64encode
from typing import Optional, Union

from mvt.common.utils import convert_datetime_to_iso

from ..base import IOSExtraction

CONF_PROFILES_DOMAIN = (
    "SysSharedContainerDomain-systemgroup.com.apple.configurationprofiles"
)


class ConfigurationProfiles(IOSExtraction):
    """This module extracts the full plist data from configuration profiles."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def serialize(self, record: dict) -> Union[dict, list]:
        if not record["install_date"]:
            return {}

        payload_name = record["plist"].get("PayloadDisplayName")
        payload_description = record["plist"].get("PayloadDescription")
        return {
            "timestamp": record["install_date"],
            "module": self.__class__.__name__,
            "event": "configuration_profile_install",
            "data": f"{record['plist']['PayloadType']} installed: {record['plist']['PayloadUUID']} "
            f"- {payload_name}: {payload_description}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            if result["plist"].get("PayloadUUID"):
                payload_content = result["plist"]["PayloadContent"][0]

                # Alert on any known malicious configuration profiles in the
                # indicator list.
                ioc = self.indicators.check_profile(result["plist"]["PayloadUUID"])
                if ioc:
                    self.log.warning(
                        "Found a known malicious configuration "
                        'profile "%s" with UUID %s',
                        result["plist"]["PayloadDisplayName"],
                        result["plist"]["PayloadUUID"],
                    )
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

                # Highlight suspicious configuration profiles which may be used
                # to hide notifications.
                if payload_content["PayloadType"] in ["com.apple.notificationsettings"]:
                    self.log.warning(
                        "Found a potentially suspicious configuration profile "
                        '"%s" with payload type %s',
                        result["plist"]["PayloadDisplayName"],
                        payload_content["PayloadType"],
                    )
                    self.detected.append(result)
                    continue

    def run(self) -> None:
        for conf_file in self._get_backup_files_from_manifest(
            domain=CONF_PROFILES_DOMAIN
        ):
            conf_rel_path = conf_file["relative_path"]

            # Filter out all configuration files that are not configuration
            # profiles.
            if not conf_rel_path or not os.path.basename(conf_rel_path).startswith(
                "profile-"
            ):
                continue

            conf_file_path = self._get_backup_file_from_id(conf_file["file_id"])
            if not conf_file_path:
                self.log.debug(
                    "Missing file %s in backup (%s)",
                    conf_file["file_id"],
                    conf_file["relative_path"],
                )
                continue

            with open(conf_file_path, "rb") as handle:
                try:
                    conf_plist = plistlib.load(handle)
                except Exception:
                    conf_plist = {}

            # TODO: Tidy up the following code hell.

            if "SignerCerts" in conf_plist:
                conf_plist["SignerCerts"] = [
                    b64encode(x) for x in conf_plist["SignerCerts"]
                ]

            if "OTAProfileStub" in conf_plist:
                if "SignerCerts" in conf_plist["OTAProfileStub"]:
                    conf_plist["OTAProfileStub"]["SignerCerts"] = [
                        b64encode(x)
                        for x in conf_plist["OTAProfileStub"]["SignerCerts"]
                    ]

                if "PayloadContent" in conf_plist["OTAProfileStub"]:
                    if (
                        "EnrollmentIdentityPersistentID"
                        in conf_plist["OTAProfileStub"]["PayloadContent"]
                    ):
                        conf_plist["OTAProfileStub"]["PayloadContent"][
                            "EnrollmentIdentityPersistentID"
                        ] = b64encode(
                            conf_plist["OTAProfileStub"]["PayloadContent"][
                                "EnrollmentIdentityPersistentID"
                            ]
                        )

            if "PushTokenDataSentToServerKey" in conf_plist:
                conf_plist["PushTokenDataSentToServerKey"] = b64encode(
                    conf_plist["PushTokenDataSentToServerKey"]
                )

            if "LastPushTokenHash" in conf_plist:
                conf_plist["LastPushTokenHash"] = b64encode(
                    conf_plist["LastPushTokenHash"]
                )

            if "PayloadContent" in conf_plist:
                for content_entry in range(len(conf_plist["PayloadContent"])):
                    if "PERSISTENT_REF" in conf_plist["PayloadContent"][content_entry]:
                        conf_plist["PayloadContent"][content_entry][
                            "PERSISTENT_REF"
                        ] = b64encode(
                            conf_plist["PayloadContent"][content_entry][
                                "PERSISTENT_REF"
                            ]
                        )

                    if (
                        "IdentityPersistentRef"
                        in conf_plist["PayloadContent"][content_entry]
                    ):
                        conf_plist["PayloadContent"][content_entry][
                            "IdentityPersistentRef"
                        ] = b64encode(
                            conf_plist["PayloadContent"][content_entry][
                                "IdentityPersistentRef"
                            ]
                        )

            self.results.append(
                {
                    "file_id": conf_file["file_id"],
                    "relative_path": conf_file["relative_path"],
                    "domain": conf_file["domain"],
                    "plist": conf_plist,
                    "install_date": convert_datetime_to_iso(
                        conf_plist.get("InstallDate")
                    ),
                }
            )

        self.log.info(
            "Extracted details about %d configuration profiles", len(self.results)
        )
