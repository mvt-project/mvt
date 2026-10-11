import json
import shlex
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from mvt.common import logo
from mvt.common.cli_plugins import (
    ANDROID_CLI_PLUGIN_GROUP,
    IOS_CLI_PLUGIN_GROUP,
    NEUTRAL_CLI_PLUGIN_GROUP,
)
from mvt.common.module_loader import MODULES_ENTRY_POINT_GROUP
from mvt.common.updates import (
    MVTUpdates,
    PluginUpdates,
    installed_plugin_distributions,
)


REPOSITORY_URL = "https://example.org/plugin.git"
INSTALLED_COMMIT = "a" * 40
REMOTE_COMMIT = "b" * 40


class FakeDistribution:
    def __init__(self, name, version="1.0.0", direct_url=None):
        self.name = name
        self.version = version
        self.direct_url = direct_url

    def read_text(self, file_name):
        if file_name == "direct_url.json" and self.direct_url is not None:
            return json.dumps(self.direct_url)
        return None


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload


def _entry_point(name, distribution, value="plugin:modules"):
    return SimpleNamespace(name=name, value=value, dist=distribution)


def _git_distribution(requested_revision=None, commit=INSTALLED_COMMIT):
    vcs_info = {"vcs": "git", "commit_id": commit}
    if requested_revision:
        vcs_info["requested_revision"] = requested_revision

    return FakeDistribution(
        "example-plugin",
        direct_url={"url": REPOSITORY_URL, "vcs_info": vcs_info},
    )


def _fake_git(stdout="", returncode=0, exception=None, calls=None):
    def run(command, **kwargs):
        if calls is not None:
            calls.append((command, kwargs))
        if exception is not None:
            raise exception
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")

    return run


@pytest.fixture
def data_folder(tmp_path, monkeypatch):
    folder = tmp_path / "mvt-data"
    monkeypatch.setattr("mvt.common.updates.MVT_DATA_FOLDER", str(folder))
    return folder


@pytest.fixture
def one_plugin(monkeypatch):
    def install(distribution):
        monkeypatch.setattr(
            "mvt.common.updates.installed_plugin_distributions",
            lambda: [distribution],
        )
        return distribution

    return install


def test_installed_plugin_distributions_covers_every_plugin_group(monkeypatch):
    zeta = FakeDistribution("zeta-plugin")
    alpha = FakeDistribution("alpha-plugin")
    neutral = FakeDistribution("neutral-plugin")

    def entry_points(*, group):
        if group == MODULES_ENTRY_POINT_GROUP:
            return [_entry_point("zeta", zeta), _entry_point("alpha", alpha)]
        if group == IOS_CLI_PLUGIN_GROUP:
            return [_entry_point("zeta-ios", zeta)]
        if group == ANDROID_CLI_PLUGIN_GROUP:
            return [_entry_point("alpha-android", alpha)]
        if group == NEUTRAL_CLI_PLUGIN_GROUP:
            return [_entry_point("shared", neutral)]
        return []

    monkeypatch.setattr(
        "mvt.common.updates.importlib.metadata.entry_points", entry_points
    )

    distributions = installed_plugin_distributions()

    assert [distribution.name for distribution in distributions] == [
        "alpha-plugin",
        "neutral-plugin",
        "zeta-plugin",
    ]


def test_installed_plugin_distributions_skips_mvt_and_orphan_entry_points(monkeypatch):
    entry_points = [
        _entry_point("builtin", FakeDistribution("mvt")),
        SimpleNamespace(name="orphan", value="plugin:modules", dist=None),
        _entry_point("plugin", FakeDistribution("example-plugin")),
    ]
    monkeypatch.setattr(
        "mvt.common.updates.importlib.metadata.entry_points",
        lambda **kwargs: entry_points,
    )

    distributions = installed_plugin_distributions()

    assert [distribution.name for distribution in distributions] == ["example-plugin"]


def test_installed_plugin_distributions_survives_broken_metadata(monkeypatch, caplog):
    def entry_points(*, group):
        raise RuntimeError("invalid package metadata")

    monkeypatch.setattr(
        "mvt.common.updates.importlib.metadata.entry_points", entry_points
    )

    assert installed_plugin_distributions() == []
    assert "Unable to discover installed plugin packages" in caplog.text


def test_index_plugin_update_is_reported(monkeypatch, data_folder, one_plugin):
    one_plugin(FakeDistribution("example-plugin", version="1.0.0"))
    monkeypatch.setattr(
        "mvt.common.updates.requests.get",
        lambda url, **kwargs: FakeResponse(payload={"info": {"version": "1.2.0"}}),
    )

    findings = PluginUpdates().check()

    assert findings == [
        {
            "name": "example-plugin",
            "installed": "1.0.0",
            "latest": "1.2.0",
            "origin": "pypi",
            "upgrade_command": "pip install -U example-plugin",
        }
    ]


def test_index_plugin_queries_the_package_index_with_the_configured_timeout(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(FakeDistribution("example-plugin"))
    requests_made = []

    def get(url, **kwargs):
        requests_made.append((url, kwargs))
        return FakeResponse(payload={"info": {"version": "1.0.0"}})

    monkeypatch.setattr("mvt.common.updates.requests.get", get)
    monkeypatch.setattr("mvt.common.updates.settings.NETWORK_TIMEOUT", 3)

    PluginUpdates().check()

    assert requests_made == [
        ("https://pypi.org/pypi/example-plugin/json", {"timeout": 3})
    ]


def test_up_to_date_index_plugin_is_not_reported(monkeypatch, data_folder, one_plugin):
    one_plugin(FakeDistribution("example-plugin", version="1.2.0"))
    monkeypatch.setattr(
        "mvt.common.updates.requests.get",
        lambda url, **kwargs: FakeResponse(payload={"info": {"version": "1.2.0"}}),
    )

    assert PluginUpdates().check() == []


def test_unpublished_plugin_is_skipped_silently(monkeypatch, data_folder, one_plugin):
    one_plugin(FakeDistribution("private-plugin"))
    monkeypatch.setattr(
        "mvt.common.updates.requests.get",
        lambda url, **kwargs: FakeResponse(status_code=404),
    )

    assert PluginUpdates().check() == []


def test_repository_plugin_following_a_branch_is_reported(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision="main"))
    calls = []
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(stdout=f"{REMOTE_COMMIT}\trefs/heads/main\n", calls=calls),
    )
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)

    findings = PluginUpdates().check()

    assert findings == [
        {
            "name": "example-plugin",
            "installed": "aaaaaaaa",
            "latest": "bbbbbbbb",
            "origin": "git",
            "upgrade_command": (
                f"pip install -U 'example-plugin @ git+{REPOSITORY_URL}@main'"
            ),
        }
    ]
    command, options = calls[0]
    assert command == ["git", "ls-remote", REPOSITORY_URL, "main"]
    assert options["env"]["GIT_TERMINAL_PROMPT"] == "0"
    # ssh asks the terminal for a passphrase or a host key unless it is told
    # not to, which git itself cannot prevent.
    assert options["env"]["GIT_SSH_COMMAND"] == (
        "ssh -o BatchMode=yes -o ConnectTimeout=10"
    )


def test_batch_mode_options_come_before_the_configured_ssh_options(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision="main"))
    calls = []
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(stdout=f"{REMOTE_COMMIT}\trefs/heads/main\n", calls=calls),
    )
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -o BatchMode=no -i /home/analyst/key")

    PluginUpdates().check()

    # ssh uses the first value it is given for a keyword, so an analyst asking
    # for prompts cannot bring them back, while their other options still
    # apply.
    assert calls[0][1]["env"]["GIT_SSH_COMMAND"] == (
        "ssh -o BatchMode=yes -o ConnectTimeout=10 -o BatchMode=no -i /home/analyst/key"
    )


def test_repository_plugin_without_a_revision_follows_the_default_branch(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution())
    calls = []
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(stdout=f"{REMOTE_COMMIT}\tHEAD\n", calls=calls),
    )

    findings = PluginUpdates().check()

    assert calls[0][0] == ["git", "ls-remote", REPOSITORY_URL, "HEAD"]
    assert findings[0]["upgrade_command"] == (
        f"pip install -U 'example-plugin @ git+{REPOSITORY_URL}'"
    )


def test_hostile_revision_cannot_inject_into_the_upgrade_command(
    monkeypatch, data_folder, one_plugin
):
    revision = "main$(id)`id`;id"
    one_plugin(_git_distribution(requested_revision=revision))
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(stdout=f"{REMOTE_COMMIT}\trefs/heads/{revision}\n"),
    )

    upgrade_command = PluginUpdates().check()[0]["upgrade_command"]

    # Single quotes are the only quoting a shell does not expand anything in.
    assert upgrade_command == (
        f"pip install -U 'example-plugin @ git+{REPOSITORY_URL}@{revision}'"
    )
    assert shlex.split(upgrade_command) == [
        "pip",
        "install",
        "-U",
        f"example-plugin @ git+{REPOSITORY_URL}@{revision}",
    ]


def test_repository_plugin_with_an_option_like_url_is_skipped(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(
        FakeDistribution(
            "example-plugin",
            direct_url={
                "url": "--upload-pack=touch /tmp/mvt",
                "vcs_info": {"vcs": "git", "commit_id": INSTALLED_COMMIT},
            },
        )
    )
    calls = []
    monkeypatch.setattr("mvt.common.updates.subprocess.run", _fake_git(calls=calls))

    assert PluginUpdates().check() == []
    assert calls == []


def test_repository_plugin_with_an_option_like_revision_is_skipped(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision="--upload-pack=touch /tmp/mvt"))
    calls = []
    monkeypatch.setattr("mvt.common.updates.subprocess.run", _fake_git(calls=calls))

    assert PluginUpdates().check() == []
    assert calls == []


def test_repository_plugin_at_the_latest_commit_is_not_reported(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision="main"))
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(stdout=f"{INSTALLED_COMMIT}\trefs/heads/main\n"),
    )

    assert PluginUpdates().check() == []


def test_commit_pinned_repository_plugin_is_never_outdated(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision=INSTALLED_COMMIT))
    calls = []
    monkeypatch.setattr("mvt.common.updates.subprocess.run", _fake_git(calls=calls))

    assert PluginUpdates().check() == []
    assert calls == []


def test_short_commit_pinned_repository_plugin_is_never_outdated(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision=INSTALLED_COMMIT[:10]))
    calls = []
    monkeypatch.setattr("mvt.common.updates.subprocess.run", _fake_git(calls=calls))

    assert PluginUpdates().check() == []
    assert calls == []


def test_tag_pinned_repository_plugin_is_never_outdated(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision="v1.0.0"))
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(stdout=f"{REMOTE_COMMIT}\trefs/tags/v1.0.0\n"),
    )

    assert PluginUpdates().check() == []


def test_repository_plugin_is_skipped_without_git(monkeypatch, data_folder, one_plugin):
    one_plugin(_git_distribution(requested_revision="main"))
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(exception=FileNotFoundError("git")),
    )

    assert PluginUpdates().check() == []


def test_repository_plugin_is_skipped_when_git_fails(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(_git_distribution(requested_revision="main"))
    monkeypatch.setattr(
        "mvt.common.updates.subprocess.run",
        _fake_git(stdout="", returncode=128),
    )

    assert PluginUpdates().check() == []


def test_local_plugin_install_is_skipped(monkeypatch, data_folder, one_plugin):
    one_plugin(
        FakeDistribution(
            "example-plugin",
            direct_url={
                "url": "file:///home/analyst/example-plugin",
                "dir_info": {"editable": True},
            },
        )
    )

    def fail(*args, **kwargs):
        raise AssertionError("a local plugin install must not be checked")

    monkeypatch.setattr("mvt.common.updates.requests.get", fail)
    monkeypatch.setattr("mvt.common.updates.subprocess.run", fail)

    assert PluginUpdates().check() == []


def test_check_stores_the_findings_and_the_check_timestamp(
    monkeypatch, data_folder, one_plugin
):
    one_plugin(FakeDistribution("example-plugin", version="1.0.0"))
    monkeypatch.setattr(
        "mvt.common.updates.requests.get",
        lambda url, **kwargs: FakeResponse(payload={"info": {"version": "1.2.0"}}),
    )
    plugin_updates = PluginUpdates()

    findings = plugin_updates.check()

    assert json.loads((data_folder / "plugin_updates.json").read_text()) == findings
    assert (data_folder / "latest_plugins_check").read_text().isdigit()
    assert PluginUpdates().get_findings() == findings


def test_findings_are_empty_before_the_first_check(data_folder):
    assert PluginUpdates().get_findings() == []


def test_malformed_cached_findings_are_dropped(data_folder):
    plugin_updates = PluginUpdates()
    usable = {
        "name": "example-plugin",
        "installed": "1.0.0",
        "latest": "1.2.0",
        "origin": "pypi",
        "upgrade_command": "pip install -U example-plugin",
    }
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "plugin_updates.json").write_text(
        json.dumps(
            [
                {"oops": 1},
                "not a finding",
                {"name": "half-plugin", "installed": "1.0.0"},
                {**usable, "latest": None},
                usable,
            ]
        ),
        encoding="utf-8",
    )

    assert plugin_updates.get_findings() == [usable]


def test_corrupt_cached_findings_are_ignored(data_folder):
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "plugin_updates.json").write_text("{ not json", encoding="utf-8")

    assert PluginUpdates().get_findings() == []


def test_cached_findings_of_upgraded_and_removed_plugins_are_dropped(
    monkeypatch, data_folder
):
    findings = [
        {
            "name": "upgraded-plugin",
            "installed": "1.0.0",
            "latest": "1.2.0",
            "origin": "pypi",
            "upgrade_command": "pip install -U upgraded-plugin",
        },
        {
            "name": "removed-plugin",
            "installed": "1.0.0",
            "latest": "1.2.0",
            "origin": "pypi",
            "upgrade_command": "pip install -U removed-plugin",
        },
        {
            "name": "example-plugin",
            "installed": "1.0.0",
            "latest": "1.2.0",
            "origin": "pypi",
            "upgrade_command": "pip install -U example-plugin",
        },
    ]
    plugin_updates = PluginUpdates()
    plugin_updates.set_findings(findings)
    monkeypatch.setattr(
        "mvt.common.updates.installed_plugin_distributions",
        lambda: [
            # The analyst upgraded this plugin since the latest check.
            FakeDistribution("upgraded-plugin", version="1.2.0"),
            FakeDistribution("example-plugin", version="1.0.0"),
        ],
    )

    assert plugin_updates.current_findings() == [findings[2]]


def test_cached_findings_of_updated_repository_plugins_are_dropped(data_folder):
    findings = [
        {
            "name": "example-plugin",
            "installed": "aaaaaaaa",
            "latest": "bbbbbbbb",
            "origin": "git",
            "upgrade_command": "pip install -U example-plugin",
        }
    ]
    plugin_updates = PluginUpdates()
    plugin_updates.set_findings(findings)

    assert plugin_updates.current_findings([_git_distribution()]) == findings
    assert (
        plugin_updates.current_findings([_git_distribution(commit=REMOTE_COMMIT)]) == []
    )


def test_corrupt_check_timestamp_does_not_raise(data_folder):
    plugin_updates = PluginUpdates()
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "latest_plugins_check").write_text("truncated", encoding="utf-8")

    assert plugin_updates.get_latest_check() == 0
    assert plugin_updates.should_check() == (True, 0)


def test_should_check_is_throttled_for_twelve_hours(data_folder):
    plugin_updates = PluginUpdates()
    plugin_updates.set_findings([])

    recent = datetime.now() - timedelta(hours=4)
    with open(plugin_updates.latest_check_path, "w", encoding="utf-8") as handle:
        handle.write(str(int(recent.timestamp())))

    should_check, hours = plugin_updates.should_check()
    assert not should_check
    assert hours == 8

    old = datetime.now() - timedelta(hours=13)
    with open(plugin_updates.latest_check_path, "w", encoding="utf-8") as handle:
        handle.write(str(int(old.timestamp())))

    assert plugin_updates.should_check() == (True, 0)


def test_should_check_without_a_previous_check(data_folder):
    assert PluginUpdates().should_check() == (True, 0)


@pytest.fixture
def no_version_check(monkeypatch):
    monkeypatch.setattr(MVTUpdates, "check", lambda self: "")
    # Keep rich from wrapping the plugin lines while they are being asserted.
    monkeypatch.setenv("COLUMNS", "200")


@pytest.fixture
def throttled_cache(monkeypatch, data_folder):
    """Fill the findings cache and put the check inside its throttle window."""

    def fill(findings, distributions):
        PluginUpdates().set_findings(findings)
        monkeypatch.setattr(
            logo, "installed_plugin_distributions", lambda: distributions
        )
        monkeypatch.setattr(PluginUpdates, "should_check", lambda self: (False, 8))
        monkeypatch.setattr(
            PluginUpdates,
            "check",
            lambda self: pytest.fail("the check must be throttled"),
        )

    return fill


def test_logo_prints_the_cached_plugin_updates(
    capsys, no_version_check, throttled_cache
):
    throttled_cache(
        [
            {
                "name": "example-plugin",
                "installed": "1.0.0",
                "latest": "1.2.0",
                "origin": "pypi",
                "upgrade_command": "pip install -U example-plugin",
            }
        ],
        [FakeDistribution("example-plugin", version="1.0.0")],
    )

    logo.check_updates(disable_indicator_check=True)

    output = capsys.readouterr().out
    assert "Plugin updates available:" in output
    assert "example-plugin  1.0.0 → 1.2.0   (pip install -U example-plugin)" in output


def test_logo_does_not_print_a_cached_update_of_an_upgraded_plugin(
    capsys, no_version_check, throttled_cache
):
    throttled_cache(
        [
            {
                "name": "example-plugin",
                "installed": "1.0.0",
                "latest": "1.2.0",
                "origin": "pypi",
                "upgrade_command": "pip install -U example-plugin",
            }
        ],
        # The analyst already upgraded the plugin the cached finding is about.
        [FakeDistribution("example-plugin", version="1.2.0")],
    )

    logo.check_updates(disable_indicator_check=True)

    assert "Plugin updates" not in capsys.readouterr().out


def test_logo_prints_nothing_when_throttled_without_findings(
    capsys, no_version_check, throttled_cache
):
    throttled_cache([], [FakeDistribution("example-plugin")])

    logo.check_updates(disable_indicator_check=True)

    assert "Plugin updates" not in capsys.readouterr().out


def test_logo_survives_a_corrupt_plugin_cache(
    monkeypatch, capsys, data_folder, no_version_check
):
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "plugin_updates.json").write_text(
        json.dumps([{"oops": 1}]), encoding="utf-8"
    )
    monkeypatch.setattr(
        logo,
        "installed_plugin_distributions",
        lambda: [FakeDistribution("example-plugin")],
    )
    monkeypatch.setattr(PluginUpdates, "should_check", lambda self: (False, 8))

    logo.check_updates(disable_indicator_check=True)

    assert "Plugin updates" not in capsys.readouterr().out


def test_logo_skips_the_plugin_check_without_plugins(
    monkeypatch, capsys, no_version_check
):
    monkeypatch.setattr(logo, "installed_plugin_distributions", list)
    monkeypatch.setattr(
        PluginUpdates,
        "should_check",
        lambda self: pytest.fail("plugins must not be checked without plugins"),
    )

    logo.check_updates(disable_indicator_check=True)

    assert "Plugin updates" not in capsys.readouterr().out


def test_logo_skips_the_plugin_check_without_network_access(
    monkeypatch, capsys, no_version_check
):
    monkeypatch.setattr("mvt.common.logo.settings.NETWORK_ACCESS_ALLOWED", False)
    monkeypatch.setattr(
        logo,
        "installed_plugin_distributions",
        lambda: pytest.fail("plugins must not be listed without network access"),
    )

    logo.check_updates(disable_indicator_check=True)

    assert "Plugin updates" not in capsys.readouterr().out


def test_logo_skips_the_plugin_check_when_update_checks_are_disabled(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        logo,
        "installed_plugin_distributions",
        lambda: pytest.fail("plugins must not be checked with --disable-update-check"),
    )

    logo.check_updates(disable_version_check=True, disable_indicator_check=True)

    assert capsys.readouterr().out == ""
