import logging
import os

from .base import AndroidExtraction

log = logging.getLogger(__name__)

class DumpsysNotification(AndroidExtraction):
    """This module extracts stats on all notifications by apps after last format/factory reset/wipe which are logged by processes. We can check all the apk module which are not cleaned up by any means """

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys notification")
        if self.output_folder:
            procstats_path = os.path.join(self.output_folder,
                                          "dumpsys_notification.txt")
            with open(procstats_path, "w") as handle:
                handle.write(output)

            log.info("Records from dumpsys notification stored at %s",
                     procstats_path)

        self._adb_disconnect()
