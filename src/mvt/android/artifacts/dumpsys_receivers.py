# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact

INTENT_NEW_OUTGOING_SMS = "android.provider.Telephony.NEW_OUTGOING_SMS"
INTENT_SMS_RECEIVED = "android.provider.Telephony.SMS_RECEIVED"
INTENT_DATA_SMS_RECEIVED = "android.intent.action.DATA_SMS_RECEIVED"
INTENT_PHONE_STATE = "android.intent.action.PHONE_STATE"
INTENT_NEW_OUTGOING_CALL = "android.intent.action.NEW_OUTGOING_CALL"


class DumpsysReceiversArtifact(AndroidArtifact):
    """
    Parser for dumpsys receivers in the package section
    """

    def check_indicators(self) -> None:
        for intent, receivers in self.results.items():
            for receiver in receivers:
                if intent == INTENT_NEW_OUTGOING_SMS:
                    self.log.info(
                        'Found a receiver to intercept outgoing SMS messages: "%s"',
                        receiver["receiver"],
                    )
                elif intent == INTENT_SMS_RECEIVED:
                    self.log.info(
                        'Found a receiver to intercept incoming SMS messages: "%s"',
                        receiver["receiver"],
                    )
                elif intent == INTENT_DATA_SMS_RECEIVED:
                    self.log.info(
                        'Found a receiver to intercept incoming data SMS message: "%s"',
                        receiver["receiver"],
                    )
                elif intent == INTENT_PHONE_STATE:
                    self.log.info(
                        "Found a receiver monitoring "
                        'telephony state/incoming calls: "%s"',
                        receiver["receiver"],
                    )
                elif intent == INTENT_NEW_OUTGOING_CALL:
                    self.log.info(
                        'Found a receiver monitoring outgoing calls: "%s"',
                        receiver["receiver"],
                    )

                if not self.indicators:
                    continue

                ioc = self.indicators.check_app_id(receiver["package_name"])
                if ioc:
                    receiver["matched_indicator"] = ioc
                    self.detected.append({intent: receiver})
                    continue

    def parse(self, output: str) -> None:
        self.results = {}

        in_receiver_resolver_table = False
        in_non_data_actions = False
        intent = None
        for line in output.splitlines():
            if line.startswith("Receiver Resolver Table:"):
                in_receiver_resolver_table = True
                continue

            if not in_receiver_resolver_table:
                continue

            if line.startswith("  Non-Data Actions:"):
                in_non_data_actions = True
                continue

            if not in_non_data_actions:
                continue

            # If we hit an empty line, the Non-Data Actions section should be
            # finished.
            if line.strip() == "":
                break

            # We detect the action name.
            if (
                line.startswith(" " * 6)
                and not line.startswith(" " * 8)
                and ":" in line
            ):
                intent = line.strip().replace(":", "")
                self.results[intent] = []
                continue

            # If we are not in an intent block yet, skip.
            if not intent:
                continue

            # If we are in a block but the line does not start with 8 spaces
            # it means the block ended a new one started, so we reset and
            # continue.
            if not line.startswith(" " * 8):
                intent = None
                continue

            # If we got this far, we are processing receivers for the
            # activities we are interested in.
            receiver = line.strip().split(" ")[1]
            package_name = receiver.split("/")[0]

            self.results[intent].append(
                {
                    "package_name": package_name,
                    "receiver": receiver,
                }
            )
