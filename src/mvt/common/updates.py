# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import importlib.metadata
import json
import logging
import os
import re
import shlex
import subprocess
from datetime import datetime
from typing import Optional, Tuple

import requests
import yaml
from packaging import version

from .cli_plugins import (
    ANDROID_CLI_PLUGIN_GROUP,
    IOS_CLI_PLUGIN_GROUP,
    NEUTRAL_CLI_PLUGIN_GROUP,
)
from .config import settings
from .indicators import MVT_DATA_FOLDER, MVT_INDICATORS_FOLDER
from .module_loader import MODULES_ENTRY_POINT_GROUP, distribution_direct_url
from .version import MVT_VERSION

log = logging.getLogger(__name__)

# In hours.
INDICATORS_CHECK_FREQUENCY = 12
PLUGINS_CHECK_FREQUENCY = 12

# The entry-point groups a package can use to extend MVT.
PLUGIN_ENTRY_POINT_GROUPS = (
    MODULES_ENTRY_POINT_GROUP,
    IOS_CLI_PLUGIN_GROUP,
    ANDROID_CLI_PLUGIN_GROUP,
    NEUTRAL_CLI_PLUGIN_GROUP,
)
SHORT_COMMIT_LENGTH = 8
# The keys every cached finding has to carry to be printed.
FINDING_KEYS = ("name", "installed", "latest", "upgrade_command")
# Options which stop ssh from waiting for an answer nobody is there to give.
_SSH_BATCH_OPTIONS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=10")
_COMMIT_PATTERN = re.compile(r"\A[0-9a-f]{7,40}\Z")


class MVTUpdates:
    def check(self) -> str:
        try:
            res = requests.get(str(settings.PYPI_UPDATE_URL), timeout=5)
        except requests.exceptions.RequestException as e:
            log.error("Failed to check for updates, skipping updates: %s", e)
            return ""
        data = res.json()
        latest_version = data.get("info", {}).get("version", "")

        if version.parse(latest_version) > version.parse(MVT_VERSION):
            return latest_version

        return ""


def installed_plugin_distributions() -> list[importlib.metadata.Distribution]:
    """Return the installed distributions which extend MVT.

    A plugin package is any distribution registering at least one entry point
    in the module or CLI command groups. Distributions are returned once each,
    sorted by name. MVT itself is not a plugin and is never returned.
    """
    distributions: dict[str, importlib.metadata.Distribution] = {}

    for group in PLUGIN_ENTRY_POINT_GROUPS:
        try:
            entry_points = importlib.metadata.entry_points(group=group)
        except Exception as exc:
            log.warning(
                "Unable to discover installed plugin packages in entry-point "
                "group %s: %s",
                group,
                exc,
            )
            continue

        for entry_point in entry_points:
            # Manually constructed entry points have no associated distribution.
            dist = getattr(entry_point, "dist", None)
            if dist is None:
                continue
            try:
                name = dist.name
            except Exception:
                continue
            if not name or name == "mvt":
                continue
            distributions.setdefault(name, dist)

    return [distributions[name] for name in sorted(distributions)]


def _is_usable_finding(finding: object) -> bool:
    """Check that a cached finding carries everything needed to print it."""
    if not isinstance(finding, dict):
        return False

    return all(
        isinstance(finding.get(key), str) and finding.get(key) for key in FINDING_KEYS
    )


def _installed_revision(
    dist: importlib.metadata.Distribution, origin: object
) -> Optional[str]:
    """Return what a plugin's installed revision is right now.

    This is the value a finding recorded as installed when it was made, so a
    finding can be compared against the current state of the installation
    without looking anything up remotely.
    """
    try:
        if origin != "git":
            return dist.version

        vcs_info = (distribution_direct_url(dist) or {}).get("vcs_info")
        if not isinstance(vcs_info, dict):
            return None

        commit = vcs_info.get("commit_id") or ""
        return commit[:SHORT_COMMIT_LENGTH] or None
    except Exception as e:
        log.debug("Failed to read the installed revision of a plugin: %s", e)
        return None


def _batch_mode_ssh_command(ssh_command: str) -> str:
    """Return an ssh command line which cannot stop to ask a question.

    ssh keeps the first value it is given for a keyword, so the batch mode
    options are inserted right after the ssh program, ahead of whatever the
    analyst configured. Their remaining options, such as which key to use,
    still apply.
    """
    try:
        arguments = shlex.split(ssh_command.strip())
    except ValueError:
        arguments = []

    if not arguments:
        arguments = ["ssh"]

    return shlex.join([arguments[0], *_SSH_BATCH_OPTIONS, *arguments[1:]])


def _revision_pins_commit(revision: str, commit: str) -> bool:
    """Check whether a requested revision pins the installed commit."""
    candidate = revision.lower()
    if not _COMMIT_PATTERN.match(candidate):
        return False

    return commit.lower().startswith(candidate)


class PluginUpdates:
    """Check for updates to the installed MVT plugin packages.

    MVT never installs or upgrades a plugin package itself. It only reports
    the command which upgrades a plugin, leaving the analyst to decide when to
    run it.
    """

    @property
    def latest_check_path(self) -> str:
        return os.path.join(MVT_DATA_FOLDER, "latest_plugins_check")

    @property
    def findings_path(self) -> str:
        return os.path.join(MVT_DATA_FOLDER, "plugin_updates.json")

    def _create_data_folder(self) -> None:
        if not os.path.exists(MVT_DATA_FOLDER):
            os.makedirs(MVT_DATA_FOLDER)

    def get_latest_check(self) -> int:
        if not os.path.exists(self.latest_check_path):
            return 0

        # A corrupt or truncated timestamp only means the next check happens
        # sooner. It must never stop MVT from running.
        try:
            with open(self.latest_check_path, "r", encoding="utf-8") as handle:
                data = handle.read().strip()
            if data:
                return int(data)
        except (OSError, ValueError) as e:
            log.debug("Failed to read the time of the latest plugin check: %s", e)

        return 0

    def set_latest_check(self) -> None:
        self._create_data_folder()
        timestamp = int(datetime.now().timestamp())
        with open(self.latest_check_path, "w", encoding="utf-8") as handle:
            handle.write(str(timestamp))

    def get_findings(self) -> list[dict]:
        """
        Return the findings of the latest check, without checking again.
        Returns an empty list if no check was ever performed.
        """
        if not os.path.exists(self.findings_path):
            return []

        try:
            with open(self.findings_path, "r", encoding="utf-8") as handle:
                findings = json.load(handle)
        except Exception as e:
            log.debug("Failed to read the cached plugin updates: %s", e)
            return []

        if not isinstance(findings, list):
            return []

        # Anything which does not look like a finding is dropped rather than
        # trusted: the cache is only a convenience.
        return [finding for finding in findings if _is_usable_finding(finding)]

    def current_findings(
        self, distributions: Optional[list[importlib.metadata.Distribution]] = None
    ) -> list[dict]:
        """
        Return the cached findings which still apply to what is installed.
        Findings about a plugin which was upgraded or removed since the latest
        check are dropped, so an update is never reported twice.
        """
        if distributions is None:
            distributions = installed_plugin_distributions()

        installed = {}
        for dist in distributions:
            try:
                installed[dist.name] = dist
            except Exception:
                continue

        current = []
        for finding in self.get_findings():
            plugin = installed.get(finding["name"])
            if plugin is None:
                continue
            if (
                _installed_revision(plugin, finding.get("origin"))
                != finding["installed"]
            ):
                continue
            current.append(finding)

        return current

    def set_findings(self, findings: list[dict]) -> None:
        self._create_data_folder()
        with open(self.findings_path, "w", encoding="utf-8") as handle:
            json.dump(findings, handle)

    def should_check(self) -> Tuple[bool, int]:
        """
        Compare time of the latest plugins check with current time.
        Returns bool and number of hours since the last check.
        """
        now = datetime.now()
        latest_check_ts = self.get_latest_check()
        latest_check_dt = datetime.fromtimestamp(latest_check_ts)

        diff = now - latest_check_dt
        diff_hours = divmod(diff.total_seconds(), 3600)[0]

        if diff_hours >= PLUGINS_CHECK_FREQUENCY:
            return True, 0

        return False, int(PLUGINS_CHECK_FREQUENCY - diff_hours)

    def _check_index_plugin(self, name: str, installed: str) -> Optional[dict]:
        """Check a plugin installed from a package index for a newer release."""
        url = f"https://pypi.org/pypi/{name}/json"
        try:
            res = requests.get(url, timeout=settings.NETWORK_TIMEOUT)
        except requests.exceptions.RequestException as e:
            log.debug("Failed to check for updates to plugin %s: %s", name, e)
            return None

        # Plugins which were never published to a public index are expected,
        # and there is nothing to compare their version against.
        if res.status_code == 404:
            return None

        if res.status_code != 200:
            log.debug(
                "Failed to check for updates to plugin %s (error %d)",
                name,
                res.status_code,
            )
            return None

        try:
            latest = res.json().get("info", {}).get("version", "")
            if not latest or version.parse(latest) <= version.parse(installed):
                return None
        except Exception as e:
            log.debug("Failed to compare the versions of plugin %s: %s", name, e)
            return None

        return {
            "name": name,
            "installed": installed,
            "latest": latest,
            "origin": "pypi",
            # The name comes from package metadata, so the command MVT
            # suggests is quoted rather than assumed to be shell-safe.
            "upgrade_command": f"pip install -U {shlex.quote(name)}",
        }

    def _git_ls_remote(self, url: str, revision: str) -> list[Tuple[str, str]]:
        """Return the remote references matching a revision, if git allows it."""
        # Neither value is trusted: they are read from the metadata of an
        # installed package and must not turn into git options.
        if url.startswith("-") or revision.startswith("-"):
            log.debug("Skipping the update check for the invalid repository %s", url)
            return []

        environment = dict(os.environ)
        # Never prompt the analyst for repository credentials. git handles its
        # own prompts, while ssh reads the terminal directly and only batch
        # mode makes it fail instead of asking.
        environment["GIT_TERMINAL_PROMPT"] = "0"
        environment["GIT_SSH_COMMAND"] = _batch_mode_ssh_command(
            environment.get("GIT_SSH_COMMAND", "")
        )

        try:
            process = subprocess.run(
                ["git", "ls-remote", url, revision],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                env=environment,
                timeout=settings.NETWORK_TIMEOUT,
                check=False,
            )
        except FileNotFoundError:
            log.debug("Could not find git, skipping the update check for %s", url)
            return []
        except (subprocess.SubprocessError, OSError) as e:
            log.debug("Failed to query the repository %s: %s", url, e)
            return []

        if process.returncode != 0:
            log.debug(
                "Failed to query the repository %s (error %d): %s",
                url,
                process.returncode,
                (process.stderr or "").strip(),
            )
            return []

        references = []
        for line in (process.stdout or "").splitlines():
            commit, _, reference = line.partition("\t")
            if commit.strip() and reference.strip():
                references.append((commit.strip(), reference.strip()))

        return references

    def _check_repository_plugin(
        self, name: str, direct_url: dict, vcs_info: dict
    ) -> Optional[dict]:
        """Check a plugin installed from a repository for a newer commit."""
        url = direct_url.get("url") or ""
        installed = vcs_info.get("commit_id") or ""
        revision = vcs_info.get("requested_revision") or ""
        if not url or not installed:
            return None

        # A plugin installed from a commit is pinned and never goes out of
        # date, no matter what the branch it came from does next.
        if revision and _revision_pins_commit(revision, installed):
            return None

        latest = ""
        wanted_reference = f"refs/heads/{revision}" if revision else "HEAD"
        for commit, reference in self._git_ls_remote(url, revision or "HEAD"):
            # Tags are pinned installs too.
            if reference.startswith("refs/tags/"):
                return None
            if reference == wanted_reference:
                latest = commit

        if not latest or latest == installed:
            return None

        requirement = f"{name} @ git+{url}"
        if revision:
            requirement += f"@{revision}"

        return {
            "name": name,
            "installed": installed[:SHORT_COMMIT_LENGTH],
            "latest": latest[:SHORT_COMMIT_LENGTH],
            "origin": "git",
            # A repository URL and a branch name can both hold characters a
            # shell would act on, so the requirement is quoted for the shell
            # the analyst is going to paste the command into.
            "upgrade_command": f"pip install -U {shlex.quote(requirement)}",
        }

    def _check_distribution(
        self, dist: importlib.metadata.Distribution
    ) -> Optional[dict]:
        try:
            name = dist.name
            installed = dist.version
        except Exception as e:
            log.debug("Failed to read the metadata of an installed plugin: %s", e)
            return None

        direct_url = distribution_direct_url(dist)
        if direct_url is None:
            return self._check_index_plugin(name, installed)

        vcs_info = direct_url.get("vcs_info")
        if isinstance(vcs_info, dict):
            return self._check_repository_plugin(name, direct_url, vcs_info)

        # Plugins installed from a local folder, including editable installs,
        # are maintained by the analyst and have nothing to check against.
        return None

    def check(self) -> list[dict]:
        """
        Check every installed plugin package for an available update.
        Returns one entry per plugin which can be upgraded.
        """
        findings = []
        for dist in installed_plugin_distributions():
            finding = self._check_distribution(dist)
            if finding:
                findings.append(finding)

        self.set_findings(findings)
        self.set_latest_check()

        return findings


class IndicatorsUpdates:
    def __init__(self) -> None:
        self.github_raw_url = "https://raw.githubusercontent.com/{}/{}/{}/{}"

        self.index_owner = "mvt-project"
        self.index_repo = "mvt-indicators"
        self.index_branch = "main"
        self.index_path = "indicators.yaml"

        if not os.path.exists(MVT_DATA_FOLDER):
            os.makedirs(MVT_DATA_FOLDER)

        self.latest_update_path = os.path.join(
            MVT_DATA_FOLDER, "latest_indicators_update"
        )
        self.latest_check_path = os.path.join(
            MVT_DATA_FOLDER, "latest_indicators_check"
        )

    def get_latest_check(self) -> int:
        if not os.path.exists(self.latest_check_path):
            return 0

        with open(self.latest_check_path, "r", encoding="utf-8") as handle:
            data = handle.read().strip()
            if data:
                return int(data)

        return 0

    def set_latest_check(self) -> None:
        timestamp = int(datetime.now().timestamp())
        with open(self.latest_check_path, "w", encoding="utf-8") as handle:
            handle.write(str(timestamp))

    def get_latest_update(self) -> int:
        """
        Check the time of the latest indicator update.
        Returns 0 if this file doesn't exists.
        """
        if not os.path.exists(self.latest_update_path):
            return 0

        with open(self.latest_update_path, "r", encoding="utf-8") as handle:
            data = handle.read().strip()
            if data:
                return int(data)

        return 0

    def set_latest_update(self) -> None:
        timestamp = int(datetime.now().timestamp())
        with open(self.latest_update_path, "w", encoding="utf-8") as handle:
            handle.write(str(timestamp))

    def get_remote_index(self) -> Optional[dict]:
        url = self.github_raw_url.format(
            self.index_owner, self.index_repo, self.index_branch, self.index_path
        )
        try:
            res = requests.get(url, timeout=5)
        except requests.exceptions.RequestException as e:
            log.error("Failed to retrieve indicators index from %s: %s", url, e)
            return None

        if res.status_code != 200:
            log.error(
                "Failed to retrieve indicators index located at %s (error %d)",
                url,
                res.status_code,
            )
            return None

        return yaml.safe_load(res.content)

    def download_remote_ioc(self, ioc_url: str) -> Optional[str]:
        try:
            res = requests.get(ioc_url, timeout=15)
        except requests.exceptions.RequestException as e:
            log.error("Failed to download indicators file from %s: %s", ioc_url, e)
            return None

        if res.status_code != 200:
            log.error(
                "Failed to download indicators file from %s (error %d)",
                ioc_url,
                res.status_code,
            )
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
        if not index:
            return

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
                log.error(
                    "Could not find a way to download indicator file for %s",
                    ioc.get("name"),
                )
                continue

            ioc_local_path = self.download_remote_ioc(ioc_url)
            if not ioc_local_path:
                continue

            log.info(
                'Downloaded indicators "%s" to %s', ioc.get("name"), ioc_local_path
            )

        self.set_latest_update()

    def _get_remote_file_latest_commit(
        self, owner: str, repo: str, branch: str, path: str
    ) -> int:
        file_commit_url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={path}&sha={branch}"
        try:
            res = requests.get(file_commit_url, timeout=5)
        except requests.exceptions.RequestException as e:
            log.error("Failed to get details about file %s: %s", file_commit_url, e)
            return -1

        if res.status_code != 200:
            log.error(
                "Failed to get details about file %s (error %d)",
                file_commit_url,
                res.status_code,
            )
            return -1

        details = res.json()
        if len(details) == 0:
            return -1

        latest_commit = details[0]
        latest_commit_date = (
            latest_commit.get("commit", {}).get("author", {}).get("date", None)
        )
        if not latest_commit_date:
            log.error(
                "Failed to retrieve date of latest update to indicators index file"
            )
            return -1

        latest_commit_dt = datetime.strptime(latest_commit_date, "%Y-%m-%dT%H:%M:%SZ")
        latest_commit_ts = int(latest_commit_dt.timestamp())

        return latest_commit_ts

    def should_check(self) -> Tuple[bool, int]:
        """
        Compare time of the latest indicator check with current time.
        Returns bool and number of hours since the last check.
        """
        now = datetime.now()
        latest_check_ts = self.get_latest_check()
        latest_check_dt = datetime.fromtimestamp(latest_check_ts)

        diff = now - latest_check_dt
        diff_hours = divmod(diff.total_seconds(), 3600)[0]

        if diff_hours >= INDICATORS_CHECK_FREQUENCY:
            return True, 0

        return False, int(INDICATORS_CHECK_FREQUENCY - diff_hours)

    def check(self) -> bool:
        self.set_latest_check()

        latest_update = self.get_latest_update()
        latest_commit_ts = self._get_remote_file_latest_commit(
            self.index_owner, self.index_repo, self.index_branch, self.index_path
        )

        if latest_update < latest_commit_ts:
            return True

        index = self.get_remote_index()
        if not index:
            return False

        for ioc in index.get("indicators", []):
            if ioc.get("type", "") != "github":
                continue

            github = ioc.get("github", {})
            owner = github.get("owner", "")
            repo = github.get("repo", "")
            branch = github.get("branch", "main")
            path = github.get("path", "")

            file_latest_commit_ts = self._get_remote_file_latest_commit(
                owner, repo, branch, path
            )
            if latest_update < file_latest_commit_ts:
                return True

        return False
