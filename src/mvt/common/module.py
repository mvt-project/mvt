# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import csv
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

from .utils import CustomJSONEncoder, exec_or_profile


class DatabaseNotFoundError(Exception):
    pass


class DatabaseCorruptedError(Exception):
    pass


class InsufficientPrivileges(Exception):
    pass


class MVTModule:
    """This class provides a base for all extraction modules."""

    enabled = True
    slug: Optional[str] = None

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[Dict[str, Any]] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Union[List[Dict[str, Any]], Dict[str, Any], None] = None,
    ) -> None:
        """Initialize module.

        :param file_path: Path to the module's database file, if there is any
        :type file_path: str
        :param target_path: Path to the target folder (backup or filesystem
                            dump)
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
        self.module_options = module_options if module_options else {}
        self.log = log
        self.indicators = None
        self.results = results if results else []
        self.detected: List[Dict[str, Any]] = []
        self.timeline: List[Dict[str, str]] = []
        self.timeline_detected: List[Dict[str, str]] = []

    @classmethod
    def from_json(cls, json_path: str, log: logging.Logger):
        with open(json_path, "r", encoding="utf-8") as handle:
            results = json.load(handle)
            if log:
                log.info('Loaded %d results from "%s"', len(results), json_path)
            return cls(results=results, log=log)

    @classmethod
    def get_slug(cls) -> str:
        """Use the module's class name to retrieve a slug"""
        if cls.slug:
            return cls.slug

        sub = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
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
                    json.dump(self.results, handle, indent=4, cls=CustomJSONEncoder)
                except Exception as exc:
                    self.log.error(
                        "Unable to store results of module %s to file %s: %s",
                        self.__class__.__name__,
                        results_file_name,
                        exc,
                    )

        if self.detected:
            detected_file_name = f"{name}_detected.json"
            detected_json_path = os.path.join(self.results_path, detected_file_name)
            with open(detected_json_path, "w", encoding="utf-8") as handle:
                json.dump(self.detected, handle, indent=4, cls=CustomJSONEncoder)

    def serialize(self, record: dict) -> Union[dict, list, None]:
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
                if isinstance(record, list):
                    self.timeline.extend(record)
                else:
                    self.timeline.append(record)

        for detected in self.detected:
            record = self.serialize(detected)
            if record:
                if isinstance(record, list):
                    self.timeline_detected.extend(record)
                else:
                    self.timeline_detected.append(record)

        # De-duplicate timeline entries.
        self.timeline = self._deduplicate_timeline(self.timeline)
        self.timeline_detected = self._deduplicate_timeline(self.timeline_detected)

    def run(self) -> None:
        """Run the main module procedure."""
        raise NotImplementedError


def run_module(module: MVTModule) -> None:
    module.log.info("Running module %s...", module.__class__.__name__)

    try:
        exec_or_profile("module.run()", globals(), locals())
    except NotImplementedError:
        module.log.exception(
            "The run() procedure of module %s was not implemented yet!",
            module.__class__.__name__,
        )
    except InsufficientPrivileges as exc:
        module.log.info(
            "Insufficient privileges for module %s: %s", module.__class__.__name__, exc
        )
    except DatabaseNotFoundError as exc:
        module.log.info(
            "There might be no data to extract by module %s: %s",
            module.__class__.__name__,
            exc,
        )
    except DatabaseCorruptedError as exc:
        module.log.error(
            "The %s module database seems to be corrupted: %s",
            module.__class__.__name__,
            exc,
        )
    except Exception as exc:
        module.log.exception(
            "Error in running extraction from module %s: %s",
            module.__class__.__name__,
            exc,
        )
    else:
        try:
            exec_or_profile("module.check_indicators()", globals(), locals())
        except NotImplementedError:
            module.log.info(
                "The %s module does not support checking for indicators",
                module.__class__.__name__,
            )
        except Exception as exc:
            module.log.exception(
                "Error when checking indicators from module %s: %s",
                module.__class__.__name__,
                exc,
            )

        else:
            if module.indicators and not module.detected:
                module.log.info(
                    "The %s module produced no detections!", module.__class__.__name__
                )

        try:
            module.to_timeline()
        except NotImplementedError:
            pass
        except Exception as exc:
            module.log.exception(
                "Error when serializing data from module %s: %s",
                module.__class__.__name__,
                exc,
            )

        module.save_to_json()


def save_timeline(timeline: list, timeline_path: str) -> None:
    """Save the timeline in a csv file.

    :param timeline: List of records to order and store
    :param timeline_path: Path to the csv file to store the timeline to

    """
    with open(timeline_path, "a+", encoding="utf-8") as handle:
        csvoutput = csv.writer(
            handle, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL, escapechar="\\"
        )
        csvoutput.writerow(["UTC Timestamp", "Plugin", "Event", "Description"])

        for event in sorted(
            timeline, key=lambda x: x["timestamp"] if x["timestamp"] is not None else ""
        ):
            csvoutput.writerow(
                [
                    event.get("timestamp"),
                    event.get("module"),
                    event.get("event"),
                    event.get("data"),
                ]
            )
