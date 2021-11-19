# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)

ACTION_NEW_OUTGOING_SMS = "android.provider.Telephony.NEW_OUTGOING_SMS"
ACTION_SMS_RECEIVED = "android.provider.Telephony.SMS_RECEIVED"
ACTION_DATA_SMS_RECEIVED = "android.intent.action.DATA_SMS_RECEIVED"
ACTION_PHONE_STATE = "android.intent.action.PHONE_STATE"


class DumpsysReceivers(AndroidExtraction):
    """This module extracts details on receivers for risky activities."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys package")
        if not output:
            return

        activity = None
        for line in output.split("\n"):
            # Find activity block markers.
            if line.strip().startswith(ACTION_NEW_OUTGOING_SMS):
                activity = ACTION_NEW_OUTGOING_SMS
                continue
            elif line.strip().startswith(ACTION_SMS_RECEIVED):
                activity = ACTION_SMS_RECEIVED
                continue
            elif line.strip().startswith(ACTION_PHONE_STATE):
                activity = ACTION_PHONE_STATE
                continue
            elif line.strip().startswith(ACTION_DATA_SMS_RECEIVED):
                activity = ACTION_DATA_SMS_RECEIVED
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

            if activity == ACTION_NEW_OUTGOING_SMS:
                self.log.info("Found a receiver to intercept outgoing SMS messages: \"%s\"",
                              receiver)
            elif activity == ACTION_SMS_RECEIVED:
                self.log.info("Found a receiver to intercept incoming SMS messages: \"%s\"",
                              receiver)
            elif activity == ACTION_DATA_SMS_RECEIVED:
                self.log.info("Found a receiver to intercept incoming data SMS message: \"%s\"",
                              receiver)
            elif activity == ACTION_PHONE_STATE:
                self.log.info("Found a receiver monitoring telephony state: \"%s\"",
                              receiver)

            self.results.append({
                "activity": activity,
                "package_name": package_name,
                "receiver": receiver,
            })

        self._adb_disconnect()
