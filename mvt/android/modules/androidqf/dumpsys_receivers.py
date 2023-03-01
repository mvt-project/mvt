# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Any, Dict, List, Optional, Union

from mvt.android.modules.adb.dumpsys_receivers import (
    INTENT_DATA_SMS_RECEIVED, INTENT_NEW_OUTGOING_CALL,
    INTENT_NEW_OUTGOING_SMS, INTENT_PHONE_STATE, INTENT_SMS_RECEIVED)
from mvt.android.parsers import parse_dumpsys_receiver_resolver_table

from .base import AndroidQFModule


class DumpsysReceivers(AndroidQFModule):
    """This module analyse dumpsys receivers"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Union[List[Any], Dict[str, Any], None] = None
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = results if results else {}

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for intent, receivers in self.results.items():
            for receiver in receivers:
                if intent == INTENT_NEW_OUTGOING_SMS:
                    self.log.info("Found a receiver to intercept outgoing SMS messages: \"%s\"",
                                  receiver["receiver"])
                elif intent == INTENT_SMS_RECEIVED:
                    self.log.info("Found a receiver to intercept incoming SMS messages: \"%s\"",
                                  receiver["receiver"])
                elif intent == INTENT_DATA_SMS_RECEIVED:
                    self.log.info("Found a receiver to intercept incoming data SMS message: \"%s\"",
                                  receiver["receiver"])
                elif intent == INTENT_PHONE_STATE:
                    self.log.info("Found a receiver monitoring "
                                  "telephony state/incoming calls: \"%s\"",
                                  receiver["receiver"])
                elif intent == INTENT_NEW_OUTGOING_CALL:
                    self.log.info("Found a receiver monitoring outgoing calls: \"%s\"",
                                  receiver["receiver"])

                ioc = self.indicators.check_app_id(receiver["package_name"])
                if ioc:
                    receiver["matched_indicator"] = ioc
                    self.detected.append({intent: receiver})

    def run(self) -> None:
        dumpsys_file = self._get_files_by_pattern("*/dumpsys.txt")
        if not dumpsys_file:
            return

        in_receivers = False
        lines = []
        with open(dumpsys_file[0]) as handle:
            for line in handle:
                if line.strip() == "DUMP OF SERVICE package:":
                    in_receivers = True
                    continue

                if not in_receivers:
                    continue

                if line.strip().startswith("------------------------------------------------------------------------------"):  # pylint: disable=line-too-long
                    break

                lines.append(line.rstrip())

        self.results = parse_dumpsys_receiver_resolver_table("\n".join(lines))

        self.log.info("Extracted receivers for %d intents", len(self.results))
