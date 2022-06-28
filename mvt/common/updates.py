# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from datetime import datetime

import requests
import yaml
from packaging import version

from .indicators import MVT_DATA_FOLDER, MVT_INDICATORS_FOLDER
from .version import MVT_VERSION

log = logging.getLogger(__name__)

# In hours.
INDICATORS_CHECK_FREQUENCY = 12


class MVTUpdates:

    def check(self) -> str:
        res = requests.get("https://pypi.org/pypi/mvt/json")
        data = res.json()
        latest_version = data.get("info", {}).get("version", "")

        if version.parse(latest_version) > version.parse(MVT_VERSION):
            return latest_version

        return ""


class IndicatorsUpdates:

    def __init__(self) -> None:
        self.github_raw_url = "https://raw.githubusercontent.com/{}/{}/{}/{}"

        self.index_owner = "mvt-project"
        self.index_repo = "mvt-indicators"
        self.index_branch = "main"
        self.index_path = "indicators.yaml"

        self.latest_update_path = os.path.join(MVT_DATA_FOLDER,
                                               "latest_indicators_update")
        self.latest_check_path = os.path.join(MVT_DATA_FOLDER,
                                              "latest_indicators_check")

    def get_latest_check(self) -> int:
        if not os.path.exists(self.latest_check_path):
            return 0

        with open(self.latest_check_path, "r") as handle:
            data = handle.read().strip()
            if data:
                return int(data)

        return 0

    def set_latest_check(self) -> None:
        timestamp = int(datetime.utcnow().timestamp())
        with open(self.latest_check_path, "w") as handle:
            handle.write(str(timestamp))

    def get_latest_update(self) -> int:
        if not os.path.exists(self.latest_update_path):
            return 0

        with open(self.latest_update_path, "r") as handle:
            data = handle.read().strip()
            if data:
                return int(data)

        return 0

    def set_latest_update(self) -> None:
        timestamp = int(datetime.utcnow().timestamp())
        with open(self.latest_update_path, "w") as handle:
            handle.write(str(timestamp))

    def get_remote_index(self) -> dict:
        url = self.github_raw_url.format(self.index_owner, self.index_repo,
                                         self.index_branch, self.index_path)
        res = requests.get(url)
        if res.status_code != 200:
            log.error("Failed to retrieve indicators index located at %s (error %d)",
                      url, res.status_code)
            return None

        return yaml.safe_load(res.content)

    def download_remote_ioc(self, ioc_url: str) -> str:
        res = requests.get(ioc_url)
        if res.status_code != 200:
            log.error("Failed to download indicators file from %s (error %d)",
                      ioc_url, res.status_code)
            return None

        clean_file_name = ioc_url.lstrip("https://").replace("/", "_")
        ioc_path = os.path.join(MVT_INDICATORS_FOLDER, clean_file_name)

        with open(ioc_path, "w", encoding="utf-8") as handle:
            handle.write(res.text)

        return ioc_path

    def update(self) -> None:
        self.set_latest_check()

        if not os.path.exists(MVT_INDICATORS_FOLDER):
            os.makedirs(MVT_INDICATORS_FOLDER)

        index = self.get_remote_index()
        for ioc in index.get("indicators", []):
            ioc_type = ioc.get("type", "")

            if ioc_type == "github":
                github = ioc.get("github", {})
                owner = github.get("owner", "")
                repo = github.get("repo", "")
                branch = github.get("branch", "main")
                path = github.get("path", "")

                ioc_url = self.github_raw_url.format(owner, repo, branch, path)
            else:
                ioc_url = ioc.get("download_url", "")

            if not ioc_url:
                log.error("Could not find a way to download indicator file for %s",
                          ioc.get("name"))
                continue

            ioc_local_path = self.download_remote_ioc(ioc_url)
            if not ioc_local_path:
                continue

            log.info("Downloaded indicators \"%s\" to %s",
                     ioc.get("name"), ioc_local_path)

        self.set_latest_update()

    def _get_remote_file_latest_commit(self, owner: str, repo: str,
                                       branch: str, path: str) -> bool:
        file_commit_url = f"https://api.github.com/repos/{self.index_owner}/{self.index_repo}/commits?path={self.index_path}"
        res = requests.get(file_commit_url)
        if res.status_code != 200:
            log.error("Failed to get details about file %s (error %d)",
                      file_commit_url, res.status_code)
            return False

        details = res.json()
        if len(details) == 0:
            return False

        latest_commit = details[0]
        latest_commit_date = latest_commit.get("commit", {}).get("author", {}).get("date", None)
        if not latest_commit_date:
            log.error("Failed to retrieve date of latest update to indicators index file")
            return False

        latest_commit_dt = datetime.strptime(latest_commit_date, '%Y-%m-%dT%H:%M:%SZ')
        latest_commit_ts = int(latest_commit_dt.timestamp())

        return latest_commit_ts

    def should_check(self) -> (bool, int):
        now = datetime.utcnow()
        latest_check_ts = self.get_latest_check()
        latest_check_dt = datetime.fromtimestamp(latest_check_ts)

        diff = now - latest_check_dt
        diff_hours = divmod(diff.total_seconds(), 3600)[0]

        if diff_hours >= INDICATORS_CHECK_FREQUENCY:
            return True, 0

        return False, INDICATORS_CHECK_FREQUENCY - diff_hours

    def check(self) -> bool:
        self.set_latest_check()

        latest_update = self.get_latest_update()
        latest_commit_ts = self._get_remote_file_latest_commit(self.index_owner,
                                                               self.index_repo,
                                                               self.index_branch,
                                                               self.index_path)

        if latest_update < latest_commit_ts:
            return True

        index = self.get_remote_index()
        for ioc in index.get("indicators", []):
            if ioc.get("type", "") != "github":
                continue

            github = ioc.get("github", {})
            owner = github.get("owner", "")
            repo = github.get("repo", "")
            branch = github.get("branch", "main")
            path = github.get("path", "")

            file_latest_commit_ts = self._get_remote_file_latest_commit(owner,
                                                                        repo,
                                                                        branch,
                                                                        path)
            if latest_update < file_latest_commit_ts:
                return True

        return False
