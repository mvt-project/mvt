# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import json
import os

import requests
from appdirs import user_data_dir

from .url import URL


class Indicators:
    """This class is used to parse indicators from a STIX2 file and provide
    functions to compare extracted artifacts to the indicators.
    """

    def __init__(self, log=None):
        self.data_dir = user_data_dir("mvt")
        self.log = log
        self.ioc_files = []
        self.total_ioc_count = 0

    def _load_downloaded_indicators(self):
        if not os.path.isdir(self.data_dir):
            return

        for f in os.listdir(self.data_dir):
            if f.lower().endswith(".stix2"):
                self.parse_stix2(os.path.join(self.data_dir, f))

    def _check_stix2_env_variable(self):
        """
        Checks if a variable MVT_STIX2 contains path to STIX Files.
        """
        if "MVT_STIX2" not in os.environ:
            return

        paths = os.environ["MVT_STIX2"].split(":")
        for path in paths:
            if os.path.isfile(path):
                self.parse_stix2(path)
            else:
                self.log.info("Invalid STIX2 path %s in MVT_STIX2 environment variable", path)

    def _generate_indicators_file(self):
        return {
            "name": "",
            "description": "",
            "file_name": "",
            "file_path": "",
            "domains": [],
            "processes": [],
            "emails": [],
            "file_names": [],
            "file_paths": [],
            "files_sha256": [],
            "app_ids": [],
            "ios_profile_ids": [],
            "count": 0,
        }

    def _add_indicator(self, ioc, ioc_file, iocs_list):
        if ioc not in iocs_list:
            iocs_list.append(ioc)
            ioc_file["count"] += 1
            self.total_ioc_count += 1

    def parse_stix2(self, file_path):
        """Extract indicators from a STIX2 file.

        :param file_path: Path to the STIX2 file to parse
        :type file_path: str

        """
        self.log.info("Parsing STIX2 indicators file at path %s", file_path)

        ioc_file = self._generate_indicators_file()
        ioc_file["file_path"] = file_path
        ioc_file["file_name"] = os.path.basename(file_path)

        with open(file_path, "r") as handle:
            try:
                data = json.load(handle)
            except json.decoder.JSONDecodeError:
                self.log.critical("Unable to parse STIX2 indicator file. The file is malformed or in the wrong format.")
                return

        for entry in data.get("objects", []):
            entry_type = entry.get("type", "")
            if entry_type == "malware":
                ioc_file["name"] = entry.get("name", "") or ioc_file["file_name"]
                ioc_file["description"] = entry.get("description", "") or ioc_file["file_name"]
                continue

            if entry_type != "indicator":
                continue

            key, value = entry.get("pattern", "").strip("[]").split("=")
            value = value.strip("'")

            if key == "domain-name:value":
                # We force domain names to lower case.
                self._add_indicator(ioc=value.lower(),
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["domains"])
            elif key == "process:name":
                self._add_indicator(ioc=value,
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["processes"])
            elif key == "email-addr:value":
                # We force email addresses to lower case.
                self._add_indicator(ioc=value.lower(),
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["emails"])
            elif key == "file:name":
                self._add_indicator(ioc=value,
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["file_names"])
            elif key == "file:path":
                self._add_indicator(ioc=value,
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["file_paths"])
            elif key == "file:hashes.sha256":
                self._add_indicator(ioc=value,
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["files_sha256"])
            elif key == "app:id":
                self._add_indicator(ioc=value,
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["app_ids"])
            elif key == "configuration-profile:id":
                self._add_indicator(ioc=value,
                                    ioc_file=ioc_file,
                                    iocs_list=ioc_file["ios_profile_ids"])

        self.log.info("Loaded %d indicators from \"%s\" indicators file",
                      ioc_file["count"], ioc_file["name"])

        self.ioc_files.append(ioc_file)

    def load_indicators_files(self, files, load_default=True):
        """
        Load a list of indicators files.
        """
        for file_path in files:
            if os.path.isfile(file_path):
                self.parse_stix2(file_path)
            else:
                self.log.warning("This indicators file %s does not exist", file_path)

        # Load downloaded indicators and any indicators from env variable.
        if load_default:
            self._load_downloaded_indicators()

        self._check_stix2_env_variable()
        self.log.info("Loaded a total of %d unique indicators", self.total_ioc_count)

    def get_iocs(self, ioc_type):
        for ioc_file in self.ioc_files:
            for ioc in ioc_file.get(ioc_type, []):
                yield {
                    "value": ioc,
                    "type": ioc_type,
                    "name": ioc_file["name"]
                }

    def check_domain(self, url):
        """Check if a given URL matches any of the provided domain indicators.

        :param url: URL to match against domain indicators
        :type url: str
        :returns: True if the URL matched an indicator, otherwise False
        :rtype: bool

        """
        # TODO: If the IOC domain contains a subdomain, it is not currently
        #       being matched.
        if not url:
            return None

        try:
            # First we use the provided URL.
            orig_url = URL(url)

            if orig_url.check_if_shortened():
                # If it is, we try to retrieve the actual URL making an
                # HTTP HEAD request.
                unshortened = orig_url.unshorten()

                # self.log.info("Found a shortened URL %s -> %s",
                #               url, unshortened)

                # Now we check for any nested URL shorteners.
                dest_url = URL(unshortened)
                if dest_url.check_if_shortened():
                    # self.log.info("Original URL %s appears to shorten another shortened URL %s ... checking!",
                    #               orig_url.url, dest_url.url)
                    return self.check_domain(dest_url.url)

                final_url = dest_url
            else:
                # If it's not shortened, we just use the original URL object.
                final_url = orig_url
        except Exception:
            # If URL parsing failed, we just try to do a simple substring
            # match.
            for ioc in self.get_iocs("domains"):
                if ioc["value"].lower() in url:
                    self.log.warning("Maybe found a known suspicious domain %s matching indicators from \"%s\"",
                                     url, ioc["name"])
                    return ioc

            # If nothing matched, we can quit here.
            return None

        # If all parsing worked, we start walking through available domain indicators.
        for ioc in self.get_iocs("domains"):
            # First we check the full domain.
            if final_url.domain.lower() == ioc["value"]:
                if orig_url.is_shortened and orig_url.url != final_url.url:
                    self.log.warning("Found a known suspicious domain %s shortened as %s matching indicators from \"%s\"",
                                     final_url.url, orig_url.url, ioc["name"])
                else:
                    self.log.warning("Found a known suspicious domain %s matching indicators from \"%s\"",
                                     final_url.url, ioc["name"])

                return ioc

            # Then we just check the top level domain.
            if final_url.top_level.lower() == ioc["value"]:
                if orig_url.is_shortened and orig_url.url != final_url.url:
                    self.log.warning("Found a sub-domain with suspicious top level %s shortened as %s matching indicators from \"%s\"",
                                     final_url.url, orig_url.url, ioc["name"])
                else:
                    self.log.warning("Found a sub-domain with a suspicious top level %s matching indicators from \"%s\"",
                                     final_url.url, ioc["name"])

                return ioc

    def check_domains(self, urls):
        """Check a list of URLs against the provided list of domain indicators.

        :param urls: List of URLs to check against domain indicators
        :type urls: list
        :returns: True if any URL matched an indicator, otherwise False
        :rtype: bool

        """
        if not urls:
            return None

        for url in urls:
            check = self.check_domain(url)
            if check:
                return check

    def check_process(self, process):
        """Check the provided process name against the list of process
        indicators.

        :param process: Process name to check against process indicators
        :type process: str
        :returns: True if process matched an indicator, otherwise False
        :rtype: bool

        """
        if not process:
            return None

        proc_name = os.path.basename(process)
        for ioc in self.get_iocs("processes"):
            if proc_name == ioc["value"]:
                self.log.warning("Found a known suspicious process name \"%s\" matching indicators from \"%s\"",
                                 process, ioc["name"])
                return ioc

            if len(proc_name) == 16:
                if ioc["value"].startswith(proc_name):
                    self.log.warning("Found a truncated known suspicious process name \"%s\" matching indicators from \"%s\"",
                                     process, ioc["name"])
                    return ioc

    def check_processes(self, processes):
        """Check the provided list of processes against the list of
        process indicators.

        :param processes: List of processes to check against process indicators
        :type processes: list
        :returns: True if process matched an indicator, otherwise False
        :rtype: bool

        """
        if not processes:
            return None

        for process in processes:
            check = self.check_process(process)
            if check:
                return check

    def check_email(self, email):
        """Check the provided email against the list of email indicators.

        :param email: Email address to check against email indicators
        :type email: str
        :returns: True if email address matched an indicator, otherwise False
        :rtype: bool

        """
        if not email:
            return None

        for ioc in self.get_iocs("emails"):
            if email.lower() == ioc["value"].lower():
                self.log.warning("Found a known suspicious email address \"%s\" matching indicators from \"%s\"",
                                 email, ioc["name"])
                return ioc

    def check_file_name(self, file_name):
        """Check the provided file name against the list of file indicators.

        :param file_name: File name to check against file
        indicators
        :type file_name: str
        :returns: True if the file name matched an indicator, otherwise False
        :rtype: bool

        """
        if not file_name:
            return None

        for ioc in self.get_iocs("file_names"):
            if ioc["value"] == file_name:
                self.log.warning("Found a known suspicious file name \"%s\" matching indicators from \"%s\"",
                                 file_name, ioc["name"])
                return ioc

    def check_file_path(self, file_path):
        """Check the provided file path against the list of file indicators (both path and name).

        :param file_path: File path or file name to check against file
        indicators
        :type file_path: str
        :returns: True if the file path matched an indicator, otherwise False
        :rtype: bool

        """
        if not file_path:
            return None

        ioc = self.check_file_name(os.path.basename(file_path))
        if ioc:
            return ioc

        for ioc in self.get_iocs("file_paths"):
            # Strip any trailing slash from indicator paths to match directories.
            if file_path.startswith(ioc["value"].rstrip("/")):
                self.log.warning("Found a known suspicious file path \"%s\" matching indicators form \"%s\"",
                                 file_path, ioc["name"])
                return ioc

    def check_profile(self, profile_uuid):
        """Check the provided configuration profile UUID against the list of indicators.

        :param profile_uuid: Profile UUID to check against configuration profile indicators
        :type profile_uuid: str
        :returns: True if the UUID in indicator list, otherwise False
        :rtype: bool

        """
        for ioc in self.get_iocs("ios_profile_ids"):
            if profile_uuid in ioc["value"]:
                self.log.warning("Found a known suspicious profile ID \"%s\" matching indicators from \"%s\"",
                                 profile_uuid, ioc["name"])
                return ioc


def download_indicators_files(log):
    """
    Download indicators from repo into MVT app data directory.
    """
    data_dir = user_data_dir("mvt")
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    # Download latest list of indicators from the MVT repo.
    res = requests.get("https://github.com/mvt-project/mvt/raw/main/public_indicators.json")
    if res.status_code != 200:
        log.warning("Unable to find retrieve list of indicators from the MVT repository.")
        return

    for ioc_entry in res.json():
        ioc_url = ioc_entry["stix2_url"]
        log.info("Downloading indicator file '%s' from '%s'", ioc_entry["name"], ioc_url)

        res = requests.get(ioc_url)
        if res.status_code != 200:
            log.warning("Could not find indicator file '%s'", ioc_url)
            continue

        clean_file_name = ioc_url.lstrip("https://").replace("/", "_")
        ioc_path = os.path.join(data_dir, clean_file_name)

        # Write file to disk. This will overwrite any older version of the STIX2 file.
        with io.open(ioc_path, "w") as f:
            f.write(res.text)

        log.info("Saved indicator file to '%s'", os.path.basename(ioc_path))
