#!/usr/bin/env python3
"""Check that the installed MVT CLI still offers what the macOS GUI relies on.

The GUI (macos/MVTGUI) does not import MVT. It builds command lines and
parses the output, so upstream changes to flags, commands, environment
variables or output formats would break it silently. This script turns those
into CI failures.

Run it after installing MVT from this checkout (pip install .):

    python macos/scripts/check_cli_contract.py

Keep EXPECTED_OPTIONS in sync with MVTCommand.options and
CommandForm.invocation() in macos/MVTGUI/Models/.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GLOBAL_OPTIONS = ["--disable-update-check", "--disable-indicator-update-check", "--verbose"]

# (script, command) -> options the GUI passes.
EXPECTED_OPTIONS = {
    ("mvt-ios", "check-backup"): ["--iocs", "--output", "--fast", "--hashes", "--module", "--list-modules"],
    ("mvt-ios", "check-fs"): ["--iocs", "--output", "--fast", "--hashes", "--module", "--list-modules"],
    ("mvt-ios", "check-sysdiagnose"): ["--iocs", "--output", "--hashes", "--module", "--list-modules"],
    ("mvt-ios", "decrypt-backup"): ["--destination", "--jobs", "--key-file", "--hashes"],
    ("mvt-ios", "extract-key"): ["--key-file"],
    ("mvt-ios", "check-iocs"): ["--iocs", "--module", "--list-modules"],
    ("mvt-ios", "version"): [],
    ("mvt-android", "check-androidqf"): [
        "--iocs", "--output", "--hashes", "--module", "--list-modules",
        "--virustotal", "--delay", "--non-interactive",
    ],
    ("mvt-android", "check-backup"): ["--iocs", "--output", "--list-modules", "--non-interactive"],
    ("mvt-android", "check-bugreport"): ["--iocs", "--output", "--module", "--list-modules", "--timezone"],
    ("mvt-android", "check-intrusion-logs"): ["--iocs", "--output", "--module", "--list-modules", "--timezone"],
    ("mvt-android", "check-iocs"): ["--iocs", "--module", "--list-modules"],
    ("mvt", "download-iocs"): [],
}

# Commands the GUI deliberately doesn't expose. Anything else upstream adds
# is reported so it can be added to the app.
NOT_IN_GUI = {"check-adb", "completion", "plugins", "version", "download-iocs"}

# Settings fields read from MVT_<NAME> environment variables that the GUI sets.
SETTINGS_ENV = ["ANDROID_BACKUP_PASSWORD", "VT_API_KEY", "IOS_BACKUP_PASSWORD"]

# Keys of alerts.json entries read by ResultsView.
ALERT_KEYS = {"level", "module", "message", "event_time", "event", "matched_indicator"}
ALERT_LEVELS = {"INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"}

# Log prefixes LogLevel.classify() in LogLine.swift looks for.
LOG_PREFIXES = ["INFO ALERT", "LOW ALERT", "MEDIUM ALERT", "HIGH ALERT", "CRITICAL ALERT", "WARNING"]

errors: list[str] = []
warnings: list[str] = []


def run(args, **kwargs):
    env = dict(os.environ, COLUMNS="200", NO_COLOR="1", TERM="dumb")
    env.setdefault("MVT_DATA_FOLDER", tempfile.mkdtemp(prefix="mvt-data-"))
    return subprocess.run(
        args, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env, **kwargs
    )


def help_text(*args) -> str:
    result = run([*args, "--help"])
    if result.returncode != 0:
        errors.append(f"`{' '.join(args)} --help` failed: {result.stderr.strip()[:300]}")
    return result.stdout


def listed_commands(help_output: str) -> set[str]:
    section = help_output.split("Commands:", 1)[-1]
    return set(re.findall(r"^\s{2}([a-z][a-z0-9-]+)\s", section, re.MULTILINE))


def check_options():
    for tool in ("mvt", "mvt-ios", "mvt-android"):
        text = help_text(tool)
        for option in GLOBAL_OPTIONS:
            if option not in text:
                errors.append(f"{tool}: global option {option} is gone")

        expected = {cmd for (t, cmd) in EXPECTED_OPTIONS if t == tool}
        available = listed_commands(text)
        for cmd in sorted(expected - available):
            errors.append(f"{tool}: command `{cmd}` is gone")
        for cmd in sorted(available - expected - NOT_IN_GUI):
            warnings.append(f"{tool}: new command `{cmd}` is not exposed in the GUI yet")

    for (tool, cmd), options in EXPECTED_OPTIONS.items():
        text = help_text(tool, cmd)
        for option in options:
            if not re.search(rf"(^|[\s,]){re.escape(option)}\b", text, re.MULTILINE):
                errors.append(f"{tool} {cmd}: option {option} is gone")


def check_environment_variables():
    from mvt.common.config import MVTSettings

    fields = set(MVTSettings.model_fields)
    for name in SETTINGS_ENV:
        if name not in fields:
            errors.append(f"setting {name} (env MVT_{name}) is gone")
    if "MVT_IOS_BACKUP_PASSWORD" not in (REPO_ROOT / "src/mvt/ios/cli.py").read_text():
        errors.append("mvt-ios no longer reads MVT_IOS_BACKUP_PASSWORD")


def check_version_output():
    result = run(["mvt-ios", "--disable-update-check", "--disable-indicator-update-check", "version"])
    if not re.search(r"^\s*Version:\s*\S+", result.stdout, re.MULTILINE):
        errors.append("`mvt-ios version` no longer prints a `Version: X` line")


def check_results_format():
    """Run a real check against the test backup and inspect its output."""
    backup = REPO_ROOT / "tests/artifacts/ios_backup"
    if not backup.is_dir():
        warnings.append("tests/artifacts/ios_backup missing; skipped the output format check")
        return

    with tempfile.TemporaryDirectory() as out:
        result = run([
            "mvt-ios", "--disable-update-check", "--disable-indicator-update-check",
            "check-backup", "--output", out, str(backup),
        ])
        if result.returncode != 0:
            errors.append(f"check-backup on the test backup failed:\n{result.stdout[-1500:]}{result.stderr[-1500:]}")
            return

        output = result.stdout + result.stderr
        seen = [p for p in LOG_PREFIXES if re.search(rf"^{p}\s", output, re.MULTILINE)]
        if not any(p.endswith("ALERT") for p in seen):
            errors.append(
                "no log line starts with an `<LEVEL> ALERT` prefix any more; "
                "update LogLevel.classify() in LogLine.swift"
            )

        for name in ("alerts.json", "info.json"):
            if not os.path.exists(os.path.join(out, name)):
                errors.append(f"check-backup no longer writes {name}")

        alerts_path = os.path.join(out, "alerts.json")
        if os.path.exists(alerts_path):
            alerts = json.load(open(alerts_path))
            if not isinstance(alerts, list) or not alerts:
                errors.append("alerts.json is no longer a non-empty list for the test backup")
            for alert in alerts[:20]:
                missing = ALERT_KEYS - set(alert)
                if missing:
                    errors.append(f"alerts.json entries lack {sorted(missing)}")
                    break
                if alert["level"] not in ALERT_LEVELS:
                    errors.append(f"unknown alert level {alert['level']!r} in alerts.json")
                    break

        info_path = os.path.join(out, "info.json")
        if os.path.exists(info_path):
            info = json.load(open(info_path))
            for key in ("target_path", "mvt_version", "date"):
                if key not in info:
                    errors.append(f"info.json lacks {key}")


def main() -> int:
    check_options()
    check_environment_variables()
    check_version_output()
    check_results_format()

    annotate = os.environ.get("GITHUB_ACTIONS") == "true"
    for message in warnings:
        print(f"::warning::{message}" if annotate else f"WARNING: {message}")
    for message in errors:
        print(f"::error::{message}" if annotate else f"ERROR: {message}")

    if errors:
        print(f"\n{len(errors)} incompatibilities with the macOS GUI.")
        return 1
    print("MVT CLI matches what the macOS GUI expects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
