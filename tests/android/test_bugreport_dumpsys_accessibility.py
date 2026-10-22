# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.android.modules.bugreport.dumpsys_accessibility import DumpsysAccessibility

from ..utils import get_artifact


def _run(content, monkeypatch, caplog):
    module = DumpsysAccessibility()
    dumpstate = f"DUMP OF SERVICE accessibility:\n{content}".encode()
    monkeypatch.setattr(module, "_get_dumpstate_file", lambda: dumpstate)
    with caplog.at_level(logging.INFO):
        module.run()


def test_logs_mixed_enabled_states(monkeypatch, caplog):
    with open(get_artifact("android_data/dumpsys_accessibility_enabled.txt")) as handle:
        _run(handle.read(), monkeypatch, caplog)

    assert (
        'Found accessibility service "com.samsung.accessibility/'
        '.universalswitch.UniversalSwitchService" (enabled: True)' in caplog.messages
    )
    assert sum("(enabled: False)" in message for message in caplog.messages) == 4
    assert (
        "Identified a total of 5 accessibility services, 1 reported enabled "
        "(0 more stated by the dump without a component name)" in caplog.messages
    )


def test_logs_enabled_count_alongside_unnamed_count(monkeypatch, caplog):
    with open(
        get_artifact("android_data/dumpsys_accessibility_v14_or_later.txt")
    ) as handle:
        _run(handle.read(), monkeypatch, caplog)

    assert (
        "Identified a total of 1 accessibility services, 1 reported enabled "
        "(1 more stated by the dump without a component name)" in caplog.messages
    )
    assert (
        sum("Found accessibility service" in message for message in caplog.messages)
        == 1
    )


def test_logs_unknown_enabled_state_without_treating_it_as_disabled(
    monkeypatch, caplog
):
    _run(
        """User state[attributes:{id=0, installedServiceCount=2}
  installed services: {
    0 : com.example/.Service
  }
""",
        monkeypatch,
        caplog,
    )

    assert (
        'Found accessibility service "com.example/.Service" (enabled: not stated)'
        in caplog.messages
    )
    assert not any("(enabled: False)" in message for message in caplog.messages)
    assert (
        "Identified a total of 1 accessibility services, 0 reported enabled "
        "(1 more stated by the dump without a component name)" in caplog.messages
    )
