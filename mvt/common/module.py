# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import io
import os
import re
import csv
import glob
import logging
import simplejson as json

from .indicators import Indicators

class MVTModule(object):
    """This class provides a base for all extraction modules."""

    enabled = True
    slug = None

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        """Initialize module.
        :param file_path: Path to the module's database file, if there is any.
        :param base_folder: Path to the base folder (backup or filesystem dump)
        :param output_folder: Folder where results will be stored
        :param fast_mode: Flag to enable or disable slow modules
        :param log: Handle to logger
        :param results: Provided list of results entries
        """
        self.file_path = file_path
        self.base_folder = base_folder
        self.output_folder = output_folder
        self.fast_mode = fast_mode
        self.log = log
        self.indicators = None
        self.results = results
        self.detected = []
        self.timeline = []
        self.timeline_detected = []

    @classmethod
    def from_json(cls, json_path, log=None):
        with open(json_path, "r") as handle:
            results = json.load(handle)
            if log:
                log.info("Loaded %d results from \"%s\"",
                         len(results), json_path)
            return cls(results=results, log=log)

    def get_slug(self):
        if self.slug:
            return self.slug

        sub = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", self.__class__.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", sub).lower()

    def _find_paths(self, root_paths):
        for root_path in root_paths:
            for found_path in glob.glob(os.path.join(self.base_folder, root_path)):
                if not os.path.exists(found_path):
                    continue
                yield found_path

    def load_indicators(self, file_path):
        self.indicators = Indicators(file_path, self.log)

    def check_indicators(self):
        """Check the results of this module against a provided list of
        indicators."""
        raise NotImplementedError

    def save_to_json(self):
        """Save the collected results to a json file.
        """
        if not self.output_folder:
            return

        name = self.get_slug()

        if self.results:
            results_file_name = f"{name}.json"
            results_json_path = os.path.join(self.output_folder, results_file_name)
            with open(results_json_path, "w") as handle:
                json.dump(self.results, handle, indent=4)

        if self.detected:
            detected_file_name = f"{name}_detected.json"
            detected_json_path = os.path.join(self.output_folder, detected_file_name)
            with open(detected_json_path, "w") as handle:
                json.dump(self.detected, handle, indent=4)

    def serialize(self, record):
        raise NotImplementedError

    def to_timeline(self):
        """Convert results into a timeline.
        """
        for result in self.results:
            record = self.serialize(result)
            if type(record) == list:
                self.timeline.extend(record)
            else:
                self.timeline.append(record)

        for detected in self.detected:
            record = self.serialize(detected)
            if type(record) == list:
                self.timeline_detected.extend(record)
            else:
                self.timeline_detected.append(record)

        # De-duplicate timeline entries
        self.timeline = self.timeline_deduplicate(self.timeline)
        self.timeline_detected = self.timeline_deduplicate(self.timeline_detected)

    def timeline_deduplicate(self, timeline):
        """Serialize entry as JSON to deduplicate repeated entries"""
        timeline_set = set()
        for record in timeline:
            timeline_set.add(json.dumps(record, sort_keys=True))
        return [json.loads(record) for record in timeline_set]

    def run(self):
        """Run the main module procedure.
        """
        raise NotImplementedError


def run_module(module):
    module.log.info("Running module %s...", module.__class__.__name__)

    try:
        module.run()
    except NotImplementedError:
        module.log.exception("The run() procedure of module %s was not implemented yet!",
                             module.__class__.__name__)
    except FileNotFoundError as e:
        module.log.info("There might be no data to extract by module %s: %s",
                        module.__class__.__name__, e)
    except Exception as e:
        module.log.exception("Error in running extraction from module %s: %s",
                             module.__class__.__name__, e)
    else:
        try:
            module.check_indicators()
        except NotImplementedError:
            pass

        try:
            module.to_timeline()
        except NotImplementedError:
            pass

        module.save_to_json()


def save_timeline(timeline, timeline_path):
    """Save the timeline in a csv file.
    :param timeline: List of records to order and store.
    :param timeline_path: Path to the csv file to store the timeline to.
    """
    with io.open(timeline_path, "a+", encoding="utf-8") as handle:
        csvoutput = csv.writer(handle, delimiter=",", quotechar="\"")
        csvoutput.writerow(["UTC Timestamp", "Plugin", "Event", "Description"])
        for event in sorted(timeline, key=lambda x: x["timestamp"] if x["timestamp"] is not None else ""):
            csvoutput.writerow([
                event["timestamp"],
                event["module"],
                event["event"],
                event["data"],
            ])
