# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import os

from .url import URL


class IndicatorsFileBadFormat(Exception):
    pass

class Indicators:
    """This class is used to parse indicators from a STIX2 file and provide
    functions to compare extracted artifacts to the indicators.
    """

    def __init__(self, log=None):
        self.log = log
        self.ioc_domains = []
        self.ioc_processes = []
        self.ioc_emails = []
        self.ioc_files = []
        self.ioc_files_sha256 = []
        self.ioc_app_ids = []
        self.ioc_count = 0

    def _add_indicator(self, ioc, iocs_list):
        if ioc not in iocs_list:
            iocs_list.append(ioc)
            self.ioc_count += 1

    def parse_stix2(self, file_path):
        """Extract indicators from a STIX2 file.

        :param file_path: Path to the STIX2 file to parse
        :type file_path: str
        """
        self.log.info("Parsing STIX2 indicators file at path %s",
                      file_path)

        with open(file_path, "r") as handle:
            try:
                data = json.load(handle)
            except json.decoder.JSONDecodeError:
                raise IndicatorsFileBadFormat("Unable to parse STIX2 indicators file, the file seems malformed or in the wrong format")

        for entry in data.get("objects", []):
            if entry.get("type", "") != "indicator":
                continue

            key, value = entry.get("pattern", "").strip("[]").split("=")
            value = value.strip("'")

            if key == "domain-name:value":
                # We force domain names to lower case.
                self._add_indicator(ioc=value.lower(),
                                    iocs_list=self.ioc_domains)
            elif key == "process:name":
                self._add_indicator(ioc=value,
                                    iocs_list=self.ioc_processes)
            elif key == "email-addr:value":
                # We force email addresses to lower case.
                self._add_indicator(ioc=value.lower(),
                                    iocs_list=self.ioc_emails)
            elif key == "file:name":
                self._add_indicator(ioc=value,
                                    iocs_list=self.ioc_files)
            elif key == "app:id":
                self._add_indicator(ioc=value,
                                    iocs_list=self.ioc_app_ids)
            elif key == "file:hashes.sha256":
                self._add_indicator(ioc=value,
                                    iocs_list=self.ioc_files_sha256)

    def check_domain(self, url) -> bool:
        """Check if a given URL matches any of the provided domain indicators.

        :param url: URL to match against domain indicators
        :type url: str
        :returns: True if the URL matched an indicator, otherwise False
        :rtype: bool
        """
        # TODO: If the IOC domain contains a subdomain, it is not currently
        # being matched.
        if not url:
            return False

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
        except Exception as e:
            # If URL parsing failed, we just try to do a simple substring
            # match.
            for ioc in self.ioc_domains:
                if ioc.lower() in url:
                    self.log.warning("Maybe found a known suspicious domain: %s", url)
                    return True

            # If nothing matched, we can quit here.
            return False

        # If all parsing worked, we start walking through available domain indicators.
        for ioc in self.ioc_domains:
            # First we check the full domain.
            if final_url.domain.lower() == ioc:
                if orig_url.is_shortened and orig_url.url != final_url.url:
                    self.log.warning("Found a known suspicious domain %s shortened as %s",
                                     final_url.url, orig_url.url)
                else:
                    self.log.warning("Found a known suspicious domain: %s", final_url.url)

                return True

            # Then we just check the top level domain.
            if final_url.top_level.lower() == ioc:
                if orig_url.is_shortened and orig_url.url != final_url.url:
                    self.log.warning("Found a sub-domain matching a known suspicious top level %s shortened as %s",
                                     final_url.url, orig_url.url)
                else:
                    self.log.warning("Found a sub-domain matching a known suspicious top level: %s", final_url.url)

                return True

        return False

    def check_domains(self, urls) -> bool:
        """Check a list of URLs against the provided list of domain indicators.

        :param urls: List of URLs to check against domain indicators
        :type urls: list
        :returns: True if any URL matched an indicator, otherwise False
        :rtype: bool
        """
        if not urls:
            return False

        for url in urls:
            if self.check_domain(url):
                return True

        return False

    def check_process(self, process) -> bool:
        """Check the provided process name against the list of process
        indicators.

        :param process: Process name to check against process indicators
        :type process: str
        :returns: True if process matched an indicator, otherwise False
        :rtype: bool
        """
        if not process:
            return False

        proc_name = os.path.basename(process)
        if proc_name in self.ioc_processes:
            self.log.warning("Found a known suspicious process name \"%s\"", process)
            return True

        if len(proc_name) == 16:
            for bad_proc in self.ioc_processes:
                if bad_proc.startswith(proc_name):
                    self.log.warning("Found a truncated known suspicious process name \"%s\"", process)
                    return True

        return False

    def check_processes(self, processes) -> bool:
        """Check the provided list of processes against the list of
        process indicators.

        :param processes: List of processes to check against process indicators
        :type processes: list
        :returns: True if process matched an indicator, otherwise False
        :rtype: bool
        """
        if not processes:
            return False

        for process in processes:
            if self.check_process(process):
                return True

        return False

    def check_email(self, email) -> bool:
        """Check the provided email against the list of email indicators.

        :param email: Email address to check against email indicators
        :type email: str
        :returns: True if email address matched an indicator, otherwise False
        :rtype: bool
        """
        if not email:
            return False

        if email.lower() in self.ioc_emails:
            self.log.warning("Found a known suspicious email address: \"%s\"", email)
            return True

        return False

    def check_file(self, file_path) -> bool:
        """Check the provided file path against the list of file indicators.

        :param file_path: File path or file name to check against file
        indicators
        :type file_path: str
        :returns: True if the file path matched an indicator, otherwise False
        :rtype: bool
        """
        if not file_path:
            return False

        file_name = os.path.basename(file_path)
        if file_name in self.ioc_files:
            self.log.warning("Found a known suspicious file: \"%s\"", file_path)
            return True

        return False
