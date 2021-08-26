# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from .base import AndroidExtraction

log = logging.getLogger(__name__)

EVENT_NEW_OUTGOING_SMS = "android.provider.Telephony.NEW_OUTGOING_SMS"
EVENT_SMS_RECEIVED = "android.provider.Telephony.SMS_RECEIVED"
EVENT_PHONE_STATE = "android.intent.action.PHONE_STATE"

class DumpsysPackages(AndroidExtraction):
    """This module extracts details on installed packages."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)


    def _find_suspicious_packages(self, output):
        """Parse dumpsys packages output to find packages with active receivers
        that could be abusive.
        """
        activity = None
        for line in output.split("\n"):
            # Find activity block markers.
            if line.strip().startswith(EVENT_NEW_OUTGOING_SMS):
                activity = EVENT_NEW_OUTGOING_SMS
                continue
            elif line.strip().startswith(EVENT_SMS_RECEIVED):
                activity = EVENT_SMS_RECEIVED
                continue
            elif line.strip().startswith(EVENT_PHONE_STATE):
                activity = EVENT_PHONE_STATE
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
            if receiver.split("/")[0] == "com.google.android.gms":
                continue

            if activity == EVENT_NEW_OUTGOING_SMS:
                self.log.warning("Found a receiver to intercept outgoing SMS messages: \"%s\"",
                    receiver)
            elif activity == EVENT_SMS_RECEIVED:
                self.log.warning("Found a receiver to intercept incoming SMS messages: \"%s\"",
                    receiver)
            elif activity == EVENT_PHONE_STATE:
                self.log.warning("Found a receiver monitoring telephony state: \"%s\"",
                    receiver)

            self.detected.append({
                "activity": activity,
                "receiver": receiver,
            })

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys package")
        self._find_suspicious_packages(output)

        if self.output_folder:
            packages_path = os.path.join(self.output_folder,
                                         "dumpsys_packages.txt")
            with open(packages_path, "w") as handle:
                handle.write(output)

            log.info("Records from dumpsys package stored at %s",
                     packages_path)

        self._adb_disconnect()
