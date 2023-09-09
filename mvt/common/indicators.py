# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Iterator, List, Optional, Union

import ahocorasick
from appdirs import user_data_dir

from .url import URL

MVT_DATA_FOLDER = user_data_dir("mvt")
MVT_INDICATORS_FOLDER = os.path.join(MVT_DATA_FOLDER, "indicators")

logger = logging.getLogger(__name__)


class Indicators:
    """This class is used to parse indicators from a STIX2 file and provide
    functions to compare extracted artifacts to the indicators.
    """

    def __init__(self, log=logger) -> None:
        self.log = log
        self.ioc_collections: List[Dict[str, Any]] = []
        self.total_ioc_count = 0

    def _load_downloaded_indicators(self) -> None:
        if not os.path.isdir(MVT_INDICATORS_FOLDER):
            return

        for ioc_file_name in os.listdir(MVT_INDICATORS_FOLDER):
            if ioc_file_name.lower().endswith(".stix2"):
                self.parse_stix2(os.path.join(MVT_INDICATORS_FOLDER, ioc_file_name))

    def _check_stix2_env_variable(self) -> None:
        """
        Checks if a variable MVT_STIX2 contains path to a STIX files.
        """
        if "MVT_STIX2" not in os.environ:
            return

        paths = os.environ["MVT_STIX2"].split(":")
        for path in paths:
            if os.path.isfile(path):
                self.parse_stix2(path)
            else:
                self.log.error(
                    "Path specified with env MVT_STIX2 is not a valid file: %s", path
                )

    def _new_collection(
        self,
        cid: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        file_name: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> dict:
        return {
            "id": cid,
            "name": name,
            "description": description,
            "stix2_file_name": file_name,
            "stix2_file_path": file_path,
            "domains": [],
            "processes": [],
            "emails": [],
            "file_names": [],
            "file_paths": [],
            "files_sha256": [],
            "app_ids": [],
            "ios_profile_ids": [],
            "android_property_names": [],
            "count": 0,
        }

    def _add_indicator(self, ioc: str, ioc_coll: dict, ioc_coll_list: list) -> None:
        ioc = ioc.strip("'")
        if ioc not in ioc_coll_list:
            ioc_coll_list.append(ioc)
            ioc_coll["count"] += 1
            self.total_ioc_count += 1

    def _process_indicator(self, indicator: dict, collection: dict) -> None:
        key, value = indicator.get("pattern", "").strip("[]").split("=")

        if key == "domain-name:value":
            # We force domain names to lower case.
            self._add_indicator(
                ioc=value.lower(),
                ioc_coll=collection,
                ioc_coll_list=collection["domains"],
            )
        elif key == "process:name":
            self._add_indicator(
                ioc=value, ioc_coll=collection, ioc_coll_list=collection["processes"]
            )
        elif key == "email-addr:value":
            # We force email addresses to lower case.
            self._add_indicator(
                ioc=value.lower(),
                ioc_coll=collection,
                ioc_coll_list=collection["emails"],
            )
        elif key == "file:name":
            self._add_indicator(
                ioc=value, ioc_coll=collection, ioc_coll_list=collection["file_names"]
            )
        elif key == "file:path":
            self._add_indicator(
                ioc=value, ioc_coll=collection, ioc_coll_list=collection["file_paths"]
            )
        elif key == "file:hashes.sha256":
            self._add_indicator(
                ioc=value, ioc_coll=collection, ioc_coll_list=collection["files_sha256"]
            )
        elif key == "app:id":
            self._add_indicator(
                ioc=value, ioc_coll=collection, ioc_coll_list=collection["app_ids"]
            )
        elif key == "configuration-profile:id":
            self._add_indicator(
                ioc=value,
                ioc_coll=collection,
                ioc_coll_list=collection["ios_profile_ids"],
            )

        elif key == "android-property:name":
            self._add_indicator(
                ioc=value,
                ioc_coll=collection,
                ioc_coll_list=collection["android_property_names"],
            )

    def parse_stix2(self, file_path: str) -> None:
        """Extract indicators from a STIX2 file.

        :param file_path: Path to the STIX2 file to parse
        :type file_path: str

        """
        self.log.info("Parsing STIX2 indicators file at path %s", file_path)

        with open(file_path, "r", encoding="utf-8") as handle:
            try:
                data = json.load(handle)
            except json.decoder.JSONDecodeError:
                self.log.critical(
                    "Unable to parse STIX2 indicator file. "
                    "The file is corrupted or in the wrong format!"
                )
                return

        malware = {}
        indicators = []
        relationships = []
        for entry in data.get("objects", []):
            entry_type = entry.get("type", "")
            if entry_type == "malware":
                malware[entry["id"]] = {
                    "name": entry["name"],
                    "description": entry.get("description", ""),
                }
            elif entry_type == "indicator":
                indicators.append(entry)
            elif entry_type == "relationship":
                relationships.append(entry)

        collections = []
        for mal_id, mal_values in malware.items():
            collection = self._new_collection(
                mal_id,
                mal_values.get("name"),
                mal_values.get("description"),
                os.path.basename(file_path),
                file_path,
            )
            collections.append(collection)

        # We loop through all indicators.
        for indicator in indicators:
            malware_id = None

            # We loop through all relationships and find the one pertinent to
            # the current indicator.
            for relationship in relationships:
                if relationship["source_ref"] != indicator["id"]:
                    continue

                # Look for a malware definition with the correct identifier.
                if relationship["target_ref"] in malware.keys():
                    malware_id = relationship["target_ref"]
                    break

            # Now we look for the correct collection matching the malware ID we
            # got from the relationship.
            for collection in collections:
                if collection["id"] == malware_id:
                    self._process_indicator(indicator, collection)
                    break

        for coll in collections:
            self.log.debug(
                'Extracted %d indicators for collection with name "%s"',
                coll["count"],
                coll["name"],
            )

        self.ioc_collections.extend(collections)

    def load_indicators_files(
        self, files: list, load_default: Optional[bool] = True
    ) -> None:
        """
        Load a list of indicators files.
        """
        for file_path in files:
            if os.path.isfile(file_path):
                self.parse_stix2(file_path)
            else:
                self.log.warning("No indicators file exists at path %s", file_path)

        # Load downloaded indicators and any indicators from env variable.
        if load_default:
            self._load_downloaded_indicators()

        self._check_stix2_env_variable()
        self.log.info("Loaded a total of %d unique indicators", self.total_ioc_count)

    def get_iocs(self, ioc_type: str) -> Iterator[Dict[str, Any]]:
        for ioc_collection in self.ioc_collections:
            for ioc in ioc_collection.get(ioc_type, []):
                yield {
                    "value": ioc,
                    "type": ioc_type,
                    "name": ioc_collection["name"],
                    "stix2_file_name": ioc_collection["stix2_file_name"],
                }

    @lru_cache()
    def get_ioc_matcher(
        self, ioc_type: Optional[str] = None, ioc_list: Optional[list] = None
    ) -> ahocorasick.Automaton:
        """
        Build an Aho-Corasick automaton from a list of iocs (i.e indicators)
        Returns an Aho-Corasick automaton

        This data-structue and algorithim allows for fast matching of a large number
        of match strings (i.e IOCs) against a large body of text. This will also
        match strings containing the IOC, so it is important to confirm the
        match is a valid IOC before using it.

            for _, ioc in domains_automaton.iter(url.domain.lower()):
                if ioc.value == url.domain.lower():
                    print(ioc)

        We use an LRU cache to avoid rebuilding the automaton every time we call a
        function such as check_domain().
        """
        automaton = ahocorasick.Automaton()
        if ioc_type:
            iocs = self.get_iocs(ioc_type)
        elif ioc_list:
            iocs = ioc_list
        else:
            raise ValueError("Must provide either ioc_tyxpe or ioc_list")

        for ioc in iocs:
            automaton.add_word(ioc["value"], ioc)
        automaton.make_automaton()
        return automaton

    @lru_cache()
    def check_domain(self, url: str) -> Union[dict, None]:
        """Check if a given URL matches any of the provided domain indicators.

        :param url: URL to match against domain indicators
        :type url: str
        :returns: Indicator details if matched, otherwise None

        """
        if not url:
            return None
        if not isinstance(url, str):
            return None

        # Create an Aho-Corasick automaton from the list of domains
        domain_matcher = self.get_ioc_matcher("domains")

        try:
            # First we use the provided URL.
            orig_url = URL(url)

            if orig_url.check_if_shortened():
                # If it is, we try to retrieve the actual URL making an
                # HTTP HEAD request.
                unshortened = orig_url.unshorten()

                self.log.debug("Found a shortened URL %s -> %s", url, unshortened)
                if unshortened is None:
                    self.log.warning("Unable to unshorten URL %s", url)
                    return None

                # Now we check for any nested URL shorteners.
                dest_url = URL(unshortened)
                if dest_url.check_if_shortened():
                    self.log.debug(
                        "Original URL %s appears to shorten another "
                        "shortened URL %s ... checking!",
                        orig_url.url,
                        dest_url.url,
                    )
                    return self.check_domain(dest_url.url)

                final_url = dest_url
            else:
                # If it's not shortened, we just use the original URL object.
                final_url = orig_url
        except Exception:
            # If URL parsing failed, we just try to do a simple substring
            # match.
            for idx, ioc in domain_matcher.iter(url):
                if ioc["value"].lower() in url:
                    self.log.warning(
                        "Maybe found a known suspicious domain %s "
                        'matching indicator "%s" from "%s"',
                        url,
                        ioc["value"],
                        ioc["name"],
                    )
                    return ioc

            # If nothing matched, we can quit here.
            return None

        # If all parsing worked, we start walking through available domain
        # indicators.
        for idx, ioc in domain_matcher.iter(final_url.domain.lower()):
            # First we check the full domain.
            if final_url.domain.lower() == ioc["value"]:
                if orig_url.is_shortened and orig_url.url != final_url.url:
                    self.log.warning(
                        "Found a known suspicious domain %s "
                        'shortened as %s matching indicator "%s" from "%s"',
                        final_url.url,
                        orig_url.url,
                        ioc["value"],
                        ioc["name"],
                    )
                else:
                    self.log.warning(
                        "Found a known suspicious domain %s "
                        'matching indicator "%s" from "%s"',
                        final_url.url,
                        ioc["value"],
                        ioc["name"],
                    )
                return ioc

        # Then we just check the top level domain.
        for idx, ioc in domain_matcher.iter(final_url.top_level.lower()):
            if final_url.top_level.lower() == ioc["value"]:
                if orig_url.is_shortened and orig_url.url != final_url.url:
                    self.log.warning(
                        "Found a sub-domain with suspicious top "
                        "level %s shortened as %s matching "
                        'indicator "%s" from "%s"',
                        final_url.url,
                        orig_url.url,
                        ioc["value"],
                        ioc["name"],
                    )
                else:
                    self.log.warning(
                        "Found a sub-domain with a suspicious top "
                        'level %s matching indicator "%s" from "%s"',
                        final_url.url,
                        ioc["value"],
                        ioc["name"],
                    )

                return ioc

        return None

    def check_domains(self, urls: list) -> Union[dict, None]:
        """Check a list of URLs against the provided list of domain indicators.

        :param urls: List of URLs to check against domain indicators
        :type urls: list
        :returns: Indicator details if matched, otherwise None

        """
        if not urls:
            return None

        for url in urls:
            check = self.check_domain(url)
            if check:
                return check

        return None

    def check_process(self, process: str) -> Union[dict, None]:
        """Check the provided process name against the list of process
        indicators.

        :param process: Process name to check against process indicators
        :type process: str
        :returns: Indicator details if matched, otherwise None

        """
        if not process:
            return None

        proc_name = os.path.basename(process)
        for ioc in self.get_iocs("processes"):
            if proc_name == ioc["value"]:
                self.log.warning(
                    'Found a known suspicious process name "%s" '
                    'matching indicators from "%s"',
                    process,
                    ioc["name"],
                )
                return ioc

            if len(proc_name) == 16:
                if ioc["value"].startswith(proc_name):
                    self.log.warning(
                        "Found a truncated known suspicious "
                        'process name "%s" matching indicators from "%s"',
                        process,
                        ioc["name"],
                    )
                    return ioc

        return None

    def check_processes(self, processes: list) -> Union[dict, None]:
        """Check the provided list of processes against the list of
        process indicators.

        :param processes: List of processes to check against process indicators
        :type processes: list
        :returns: Indicator details if matched, otherwise None

        """
        if not processes:
            return None

        for process in processes:
            check = self.check_process(process)
            if check:
                return check

        return None

    def check_email(self, email: str) -> Union[dict, None]:
        """Check the provided email against the list of email indicators.

        :param email: Email address to check against email indicators
        :type email: str
        :returns: Indicator details if matched, otherwise None

        """
        if not email:
            return None

        for ioc in self.get_iocs("emails"):
            if email.lower() == ioc["value"].lower():
                self.log.warning(
                    'Found a known suspicious email address "%s" '
                    'matching indicators from "%s"',
                    email,
                    ioc["name"],
                )
                return ioc

        return None

    def check_file_name(self, file_name: str) -> Union[dict, None]:
        """Check the provided file name against the list of file indicators.

        :param file_name: File name to check against file
        indicators
        :type file_name: str
        :returns: Indicator details if matched, otherwise None

        """
        if not file_name:
            return None

        for ioc in self.get_iocs("file_names"):
            if ioc["value"] == file_name:
                self.log.warning(
                    'Found a known suspicious file name "%s" '
                    'matching indicators from "%s"',
                    file_name,
                    ioc["name"],
                )
                return ioc

        return None

    def check_file_path(self, file_path: str) -> Union[dict, None]:
        """Check the provided file path against the list of file indicators
        (both path and name).

        :param file_path: File path or file name to check against file
        indicators
        :type file_path: str
        :returns: Indicator details if matched, otherwise None

        """
        if not file_path:
            return None

        ioc = self.check_file_name(os.path.basename(file_path))
        if ioc:
            return ioc

        for ioc in self.get_iocs("file_paths"):
            # Strip any trailing slash from indicator paths to match
            # directories.
            if file_path.startswith(ioc["value"].rstrip("/")):
                self.log.warning(
                    'Found a known suspicious file path "%s" '
                    'matching indicators form "%s"',
                    file_path,
                    ioc["name"],
                )
                return ioc

        return None

    def check_file_path_process(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Check the provided file path contains a process name from the
        list of indicators

        :param file_path: File path or file name to check against file
        indicators
        :type file_path: str
        :returns: Indicator details if matched, otherwise None

        """
        if not file_path:
            return None

        for ioc in self.get_iocs("processes"):
            parts = file_path.split("/")
            if ioc["value"] in parts:
                self.log.warning(
                    "Found known suspicious process name mentioned in file at "
                    'path "%s" matching indicators from "%s"',
                    file_path,
                    ioc["name"],
                )
                return ioc

        return None

    def check_profile(self, profile_uuid: str) -> Union[dict, None]:
        """Check the provided configuration profile UUID against the list of
        indicators.

        :param profile_uuid: Profile UUID to check against configuration profile
                             indicators
        :type profile_uuid: str
        :returns: Indicator details if matched, otherwise None

        """
        if not profile_uuid:
            return None

        for ioc in self.get_iocs("ios_profile_ids"):
            if profile_uuid in ioc["value"]:
                self.log.warning(
                    'Found a known suspicious profile ID "%s" '
                    'matching indicators from "%s"',
                    profile_uuid,
                    ioc["name"],
                )
                return ioc

        return None

    def check_file_hash(self, file_hash: str) -> Union[dict, None]:
        """Check the provided SHA256 file hash against the list of indicators.

        :param file_hash: SHA256 hash to check
        :type file_hash: str
        :returns: Indicator details if matched, otherwise None

        """
        if not file_hash:
            return None

        for ioc in self.get_iocs("files_sha256"):
            if file_hash.lower() == ioc["value"].lower():
                self.log.warning(
                    'Found a known suspicious file with hash "%s" '
                    'matching indicators from "%s"',
                    file_hash,
                    ioc["name"],
                )
                return ioc

        return None

    def check_app_id(self, app_id: str) -> Union[dict, None]:
        """Check the provided app identifier (typically an Android package name)
        against the list of indicators.

        :param app_id: App ID to check against the list of indicators
        :type app_id: str
        :returns: Indicator details if matched, otherwise None

        """
        if not app_id:
            return None

        for ioc in self.get_iocs("app_ids"):
            if app_id.lower() == ioc["value"].lower():
                self.log.warning(
                    'Found a known suspicious app with ID "%s" '
                    'matching indicators from "%s"',
                    app_id,
                    ioc["name"],
                )
                return ioc

        return None

    def check_android_property_name(self, property_name: str) -> Optional[dict]:
        """Check the android property name against the list of indicators.

        :param property_name: Name of the Android property
        :type property_name: str
        :returns: Indicator details if matched, otherwise None

        """
        if property_name is None:
            return None

        for ioc in self.get_iocs("android_property_names"):
            if property_name.lower() == ioc["value"].lower():
                self.log.warning(
                    'Found a known suspicious Android property "%s" '
                    'matching indicators from "%s"',
                    property_name,
                    ioc["name"],
                )
                return ioc

        return None
