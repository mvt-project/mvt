# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import csv
import logging
import os
import re
from typing import Callable

import simplejson as json


class DatabaseNotFoundError(Exception):
    pass


class DatabaseCorruptedError(Exception):
    pass


class InsufficientPrivileges(Exception):
    pass


class MVTModule(object):
    """This class provides a base for all extraction modules."""

    enabled = True
    slug = None

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = None):
        """Initialize module.

        :param file_path: Path to the module's database file, if there is any
        :type file_path: str
        :param target_path: Path to the target folder (backup or filesystem dump)
        :type file_path: str
        :param results_path: Folder where results will be stored
        :type results_path: str
        :param fast_mode: Flag to enable or disable slow modules
        :type fast_mode: bool
        :param log: Handle to logger
        :param results: Provided list of results entries
        :type results: list
        """
        self.file_path = file_path
        self.target_path = target_path
        self.results_path = results_path
        self.fast_mode = fast_mode
        self.log = log
        self.indicators = None
        self.results = results if results else []
        self.detected = []
        self.timeline = []
        self.timeline_detected = []

    @classmethod
    def from_json(cls, json_path: str, log: logging.Logger = None):
        with open(json_path, "r", encoding="utf-8") as handle:
            results = json.load(handle)
            if log:
                log.info("Loaded %d results from \"%s\"",
                         len(results), json_path)
            return cls(results=results, log=log)

    def get_slug(self) -> str:
        """Use the module's class name to retrieve a slug"""
        if self.slug:
            return self.slug

        sub = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", self.__class__.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", sub).lower()

    def check_indicators(self) -> None:
        """Check the results of this module against a provided list of
        indicators.


        """
        raise NotImplementedError

    def save_to_json(self) -> None:
        """Save the collected results to a json file."""
        if not self.results_path:
            return

        name = self.get_slug()

        if self.results:
            results_file_name = f"{name}.json"
            results_json_path = os.path.join(self.results_path, results_file_name)
            with open(results_json_path, "w", encoding="utf-8") as handle:
                try:
                    json.dump(self.results, handle, indent=4, default=str)
                except Exception as e:
                    self.log.error("Unable to store results of module %s to file %s: %s",
                                   self.__class__.__name__, results_file_name, e)

        if self.detected:
            detected_file_name = f"{name}_detected.json"
            detected_json_path = os.path.join(self.results_path, detected_file_name)
            with open(detected_json_path, "w", encoding="utf-8") as handle:
                json.dump(self.detected, handle, indent=4, default=str)

    def serialize(self, record: dict) -> None:
        raise NotImplementedError

    @staticmethod
    def _deduplicate_timeline(timeline: list) -> list:
        """Serialize entry as JSON to deduplicate repeated entries

        :param timeline: List of entries from timeline to deduplicate

        """
        timeline_set = set()
        for record in timeline:
            timeline_set.add(json.dumps(record, sort_keys=True))
        return [json.loads(record) for record in timeline_set]

    def to_timeline(self) -> None:
        """Convert results into a timeline."""
        for result in self.results:
            record = self.serialize(result)
            if record:
                if type(record) == list:
                    self.timeline.extend(record)
                else:
                    self.timeline.append(record)

        for detected in self.detected:
            record = self.serialize(detected)
            if record:
                if type(record) == list:
                    self.timeline_detected.extend(record)
                else:
                    self.timeline_detected.append(record)

        # De-duplicate timeline entries.
        self.timeline = self._deduplicate_timeline(self.timeline)
        self.timeline_detected = self._deduplicate_timeline(self.timeline_detected)

    def run(self) -> None:
        """Run the main module procedure."""
        raise NotImplementedError


def run_module(module: Callable) -> None:
    module.log.info("Running module %s...", module.__class__.__name__)

    try:
        module.run()
    except NotImplementedError:
        module.log.exception("The run() procedure of module %s was not implemented yet!",
                             module.__class__.__name__)
    except InsufficientPrivileges as e:
        module.log.info("Insufficient privileges for module %s: %s", module.__class__.__name__, e)
    except DatabaseNotFoundError as e:
        module.log.info("There might be no data to extract by module %s: %s",
                        module.__class__.__name__, e)
    except DatabaseCorruptedError as e:
        module.log.error("The %s module database seems to be corrupted: %s",
                         module.__class__.__name__, e)
    except Exception as e:
        module.log.exception("Error in running extraction from module %s: %s",
                             module.__class__.__name__, e)
    else:
        try:
            module.check_indicators()
        except NotImplementedError:
            module.log.info("The %s module does not support checking for indicators",
                            module.__class__.__name__)
            pass
        else:
            if module.indicators and not module.detected:
                module.log.info("The %s module produced no detections!",
                                module.__class__.__name__)

        try:
            module.to_timeline()
        except NotImplementedError:
            pass

        module.save_to_json()


def save_timeline(timeline: list, timeline_path: str) -> None:
    """Save the timeline in a csv file.

    :param timeline: List of records to order and store
    :param timeline_path: Path to the csv file to store the timeline to

    """
    with open(timeline_path, "a+", encoding="utf-8") as handle:
        csvoutput = csv.writer(handle, delimiter=",", quotechar="\"",
                               quoting=csv.QUOTE_ALL)
        csvoutput.writerow(["UTC Timestamp", "Plugin", "Event", "Description"])
        for event in sorted(timeline, key=lambda x: x["timestamp"] if x["timestamp"] is not None else ""):
            csvoutput.writerow([
                event.get("timestamp"),
                event.get("module"),
                event.get("event"),
                event.get("data"),
            ])
