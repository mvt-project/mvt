# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact
from .package_resolvers import parse_resolver_table

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
        for receiver in self.results:
            intent = receiver["key"]
            if intent == INTENT_NEW_OUTGOING_SMS:
                self.log.info(
                    'Found a receiver to intercept outgoing SMS messages: "%s"',
                    receiver["component"],
                )
            elif intent == INTENT_SMS_RECEIVED:
                self.log.info(
                    'Found a receiver to intercept incoming SMS messages: "%s"',
                    receiver["component"],
                )
            elif intent == INTENT_DATA_SMS_RECEIVED:
                self.log.info(
                    'Found a receiver to intercept incoming data SMS message: "%s"',
                    receiver["component"],
                )
            elif intent == INTENT_PHONE_STATE:
                self.log.info(
                    'Found a receiver monitoring telephony state/incoming calls: "%s"',
                    receiver["component"],
                )
            elif intent == INTENT_NEW_OUTGOING_CALL:
                self.log.info(
                    'Found a receiver monitoring outgoing calls: "%s"',
                    receiver["component"],
                )

            if not self.indicators:
                continue

            ioc_match = self.indicators.check_app_id(receiver["package_name"])
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message,
                    "",
                    receiver,
                    matched_indicator=ioc_match.ioc,
                )

    def parse(self, output: str) -> None:
        self.results = parse_resolver_table(output, "Receiver")
