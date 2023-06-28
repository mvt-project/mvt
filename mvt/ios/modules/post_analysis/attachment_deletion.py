import logging
import datetime
from typing import Optional

from mvt.common.module import PostAnalysisModule


class PostAttachmentDeletion(PostAnalysisModule):
    """
    Heuristic detection for attachment deletion in a cert time period.


    This module implements a hueuristic detection for a multiple iOS SMS attachmemt being deleted
    in a short period of time. This is a similar concept to the following script used
    by Kaspersky Labs to detect infections with the Triangulation iOS malware:
    https://github.com/KasperskyLab/triangle_check/blob/main/triangle_check/__init__.py
    """
    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

        self.required_modules = ["manifest"]


    def load_locationd_events(self):
        locationd_clients = self.results["locationd_clients"]
        locations_stopped_event = [event for event in locationd_clients if "LocationTimeStopped" in event]
        return locations_stopped_event

    def run(self) -> None:
        """
        Run the post-processing module.

        The logical is to look for all SMS attachment directories which were recently created
        shortly before their last modified time, but which have no contained files.
        """
        for module in self.required_modules:
            if module not in self.results:
                raise Exception(f"Required module {module} was not found in results. Did you run the required modules?")

        locationd_events = []
        locationd_client_iocs = [
            "com.apple.locationd.bundle-/System/Library/LocationBundles/IonosphereHarvest.bundle",
            "com.apple.locationd.bundle-/System/Library/LocationBundles/WRMLinkSelection.bundle"
        ]
        for event in self.load_locationd_events():
            for ioc in locationd_client_iocs:
                if ioc in event["Registered"]:
                    locationd_events.append(event)
                    print(event)



        # Filter the relevant events from the manifest:
        events_by_time = {}
        sms_files = [event for event in self.results["manifest"] if event["relative_path"].startswith("Library/SMS/Attachments/")]
        attachment_folders = {}
        for record in sorted(sms_files, key=lambda x: x["relative_path"]):
            num_path_segments = record["relative_path"].count('/')
            # Skip entries with a full-path
            # if not (num_path_segments == 3 or num_path_segments == 4):
            #     continue

            attachment_root = "/".join(record["relative_path"].split('/', 5)[:5])
            attachment_folder = attachment_folders.get(attachment_root, [])
            attachment_folder.append(record)
            attachment_folders[attachment_root] = attachment_folder

        # Look for directories containing no files, which had a short lifespan
        for key, items in attachment_folders.items():
            has_files = any([item["flags"] == 1 for item in items])
            if has_files:
                continue

            for item in sorted(items, key=lambda x: x["created"]):
                # item_created = datetime.datetime.strptime(item["created"], "%Y-%m-%d %H:%M:%S.%f")
                item_modified = datetime.datetime.strptime(item["modified"], "%Y-%m-%d %H:%M:%S.%f") # M
                status_changed = datetime.datetime.strptime(item["status_changed"], "%Y-%m-%d %H:%M:%S.%f") # C

                # self.append_timeline(fs_stat['LastModified'], ('M', relativePath))
                # self.append_timeline(fs_stat['LastStatusChange'], ('C', relativePath))
                # self.append_timeline(fs_stat['Birth'], ('B', relativePath))


                # Skip items which were created and modified at the same time, likely never had files.
                # print(item["relative_path"], status_changed, item_modified)
                if item_modified == status_changed:
                    print("changed == modified", item["relative_path"], status_changed, item_modified)
                    continue

                if (item_modified - status_changed): # < datetime.timedelta(minutes=10):
                     self.log.info(f"Possible attachment deletion. Attachment folder '{key}' with no files, created and modified within 10 minutes. '{item['relative_path']}' created {item_created}, modified {item_modified})")
