# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.whatsapp import Whatsapp

from ..utils import get_ios_backup_folder


def test_extraction():
    m = Whatsapp(target_path=get_ios_backup_folder())
    run_module(m)

    messages = [r for r in m.results if "ZTEXT" in r]
    sessions = [r for r in m.results if r.get("record_type") == "chat_session"]
    pairs = [
        r for r in m.results
        if r.get("record_type") == "lid_phone_number_pair"
    ]
    assert len(messages) == 3
    assert len(sessions) == 2
    assert len(pairs) == 1

    assert pairs[0]["lid"] == "100000000000001"
    assert pairs[0]["phone_number"] == "14155550100"
    assert pairs[0]["pair_timestamp"] == "2025-08-25 07:33:20.000000"

    linked = next(r for r in messages if r.get("links"))
    assert linked["links"] == ["https://example.org/news"]

    alice = next(s for s in sessions if s["partner_name"] == "Alice Example")
    assert alice["contact_jid"] == "100000000000001@lid"
    assert alice["partner_resolved_phone_number"] == "+14155550100"
    assert alice["first_stored_message_date"] == "2025-08-27 15:06:40.000000"
    assert alice["last_message_date"] == "2025-08-28 18:53:20.000000"
    assert alice["group_creation_date"] is None
    assert alice["stored_message_count"] == 2

    group = next(s for s in sessions if s["partner_name"] == "Example Group")
    assert group["group_creation_date"] == "2025-08-21 20:13:20.000000"
    assert group["first_stored_message_date"] == "2025-08-29 22:40:00.000000"
    # The last stored message predates the session's own last-message date:
    # the newest message in this chat was deleted.
    assert group["last_stored_message_date"] == "2025-08-29 22:40:00.000000"
    assert group["last_message_date"] == "2025-08-31 02:26:40.000000"

    # 3 message events, first/last per chat, the group creation and the
    # LID-phone number pair.
    assert len(m.timeline) == 9
    events = {
        (entry["event"], entry["timestamp"]): entry["data"]
        for entry in m.timeline
    }
    # Alice's session is keyed by LID but labelled with the phone number
    # resolved through LID.sqlite.
    assert events[("chat_first_message", "2025-08-27 15:06:40.000000")] == (
        "First stored message in WhatsApp chat with "
        "'Alice Example' (+14155550100)"
    )
    assert events[("chat_last_message", "2025-08-28 18:53:20.000000")] == (
        "Last message in WhatsApp chat with "
        "'Alice Example' (+14155550100)"
    )
    assert events[("lid_pair_recorded", "2025-08-25 07:33:20.000000")] == (
        "WhatsApp associated LID 100000000000001 with "
        "phone number 14155550100"
    )
    assert events[("group_created", "2025-08-21 20:13:20.000000")] == (
        "WhatsApp group chat 'Example Group' "
        "(120000000000000001@g.us) was created"
    )
    assert ("chat_first_message", "2025-08-29 22:40:00.000000") in events
    assert ("chat_last_message", "2025-08-31 02:26:40.000000") in events

    assert len(m.alertstore.alerts) == 0


def test_collect_url_results_includes_expansion():
    module = Whatsapp(
        results=[
            {
                "links": ["https://bit.ly/message"],
                "isodate": "2026-07-29 12:00:00.000000",
            }
        ]
    )
    module.indicators = Indicators(log=logging.getLogger())
    module.indicators.resolved_urls["https://bit.ly/message"] = (
        "https://example.org/landing"
    )

    module.collect_url_results()

    assert module.url_results == [
        {
            "url": "https://bit.ly/message",
            "expanded_url": "https://example.org/landing",
            "timestamp": "2026-07-29 12:00:00.000000",
            "source": "whatsapp",
        }
    ]
