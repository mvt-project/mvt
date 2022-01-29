# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)

INTENT_NEW_OUTGOING_SMS = "android.provider.Telephony.NEW_OUTGOING_SMS"
INTENT_SMS_RECEIVED = "android.provider.Telephony.SMS_RECEIVED"
INTENT_DATA_SMS_RECEIVED = "android.intent.action.DATA_SMS_RECEIVED"
INTENT_PHONE_STATE = "android.intent.action.PHONE_STATE"
INTENT_NEW_OUTGOING_CALL = "android.intent.action.NEW_OUTGOING_CALL"


class DumpsysReceivers(AndroidExtraction):
    """This module extracts details on receivers for risky activities."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self):
        for result in self.results:
            if result["activity"] == INTENT_NEW_OUTGOING_SMS:
                self.log.info("Found a receiver to intercept outgoing SMS messages: \"%s\"",
                              result["receiver"])
            elif result["activity"] == INTENT_SMS_RECEIVED:
                self.log.info("Found a receiver to intercept incoming SMS messages: \"%s\"",
                              result["receiver"])
            elif result["activity"] == INTENT_DATA_SMS_RECEIVED:
                self.log.info("Found a receiver to intercept incoming data SMS message: \"%s\"",
                              result["receiver"])
            elif result["activity"] == INTENT_PHONE_STATE:
                self.log.info("Found a receiver monitoring telephony state/incoming calls: \"%s\"",
                              result["receiver"])
            elif result["activity"] == INTENT_NEW_OUTGOING_CALL:
                self.log.info("Found a receiver monitoring outgoing calls: \"%s\"",
                              result["receiver"])

    def parse_dumpsys_package(self, data):
        """
        Parse content of dumpsys package
        """
        activity = None
        for line in data:
            # Find activity block markers.
            if line.strip().startswith(INTENT_NEW_OUTGOING_SMS):
                activity = INTENT_NEW_OUTGOING_SMS
                continue
            elif line.strip().startswith(INTENT_SMS_RECEIVED):
                activity = INTENT_SMS_RECEIVED
                continue
            elif line.strip().startswith(INTENT_PHONE_STATE):
                activity = INTENT_PHONE_STATE
                continue
            elif line.strip().startswith(INTENT_DATA_SMS_RECEIVED):
                activity = INTENT_DATA_SMS_RECEIVED
                continue
            elif line.strip().startswith(INTENT_NEW_OUTGOING_CALL):
                activity = INTENT_NEW_OUTGOING_CALL
                continue

            # If we are not in an activity block yet, skip.
            if not activity:
                continue

            # If we are in a block but the line does not start with 8 spaces
            # it means the block ended a new one started, so we reset and
            # continue.
            if not line.startswith(" " * 8):
                activity = None
                continue

            # If we got this far, we are processing receivers for the
            # activities we are interested in.
            receiver = line.strip().split(" ")[1]
            package_name = receiver.split("/")[0]
            if package_name == "com.google.android.gms":
                continue

            self.results.append({
                "activity": activity,
                "package_name": package_name,
                "receiver": receiver,
            })

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys package")
        if not output:
            return
        self.parse_dumpsys_package(output.split("\n"))
        self._adb_disconnect()
