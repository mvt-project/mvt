# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.module import run_module
from mvt.ios.modules.mixed.interactionc import InteractionC
from mvt.ios.modules.mixed.whatsapp_contacts import WhatsappContacts

from ..utils import get_ios_backup_folder


class TestInteractionCModule:
    def test_extraction_with_whatsapp_contacts(self):
        contacts = WhatsappContacts(target_path=get_ios_backup_folder())
        run_module(contacts)

        m = InteractionC(target_path=get_ios_backup_folder())
        m.dependency_modules = {WhatsappContacts: contacts}
        run_module(m)

        assert len(m.results) == 3

        incoming = next(
            r for r in m.results if r["sender_identifier"] == "100000000000001@lid"
        )
        assert incoming["direction"] == "INCOMING"
        assert incoming["sender_resolved_phone_number"] == "+14155550100"
        assert incoming["sender_resolved_name"] == "Alice Example"

        outgoing = next(
            r for r in m.results if r["direction"] == "OUTGOING"
        )
        assert outgoing["recipient_identifier"] == "+14155550100"
        assert outgoing["recipient_resolved_name"] == "Alice Example"
        assert outgoing["domain_resolved_phone_number"] == "+14155550100"
        assert outgoing["domain_resolved_name"] == "Alice Example"

        sms = next(
            r for r in m.results if r["bundle_id"] == "com.apple.MobileSMS"
        )
        assert sms.get("sender_resolved_name") is None
        assert sms["sender_display_name"] == "Bob Example"

        events = [entry["data"] for entry in m.timeline]
        assert (
            "[net.whatsapp.WhatsApp] INCOMING from "
            "Alice Example (+14155550100) to local user" in events
        )
        assert (
            "[net.whatsapp.WhatsApp] OUTGOING from local user to "
            "Alice Example (+14155550100)" in events
        )
        assert (
            "[com.apple.MobileSMS] INCOMING from "
            "Bob Example (+14155550101) to local user" in events
        )

    def test_extraction_without_whatsapp_contacts(self):
        # Without the WhatsappContacts dependency the module still runs, and
        # unresolvable LIDs are shown as-is.
        m = InteractionC(target_path=get_ios_backup_folder())
        run_module(m)

        assert len(m.results) == 3
        events = [entry["data"] for entry in m.timeline]
        assert (
            "[net.whatsapp.WhatsApp] INCOMING from "
            "100000000000001@lid to local user" in events
        )
        assert (
            "[net.whatsapp.WhatsApp] OUTGOING from local user to "
            "+14155550100" in events
        )
