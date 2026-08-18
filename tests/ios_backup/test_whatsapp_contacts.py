# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.module import run_module
from mvt.ios.modules.mixed.whatsapp_contacts import WhatsappContacts

from ..utils import get_ios_backup_folder


class TestWhatsappContactsModule:
    def test_extraction(self):
        m = WhatsappContacts(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 2

        alice = next(r for r in m.results if r["given_name"] == "Alice")
        assert alice["full_name"] == "Alice Example"
        assert alice["phone_number"] == "+14155550100"
        assert alice["whatsapp_id"] == "14155550100@s.whatsapp.net"
        assert alice["lid"] == "100000000000001@lid"
        assert alice["user_name"] == "alice.example"
        assert alice["disappearing_mode_duration"] == 86400.0
        assert alice["disappearing_mode_is_on"] is True
        assert alice["disappearing_mode_label"] == "24 hours"
        assert alice["disappearing_mode_timestamp"] == "2025-07-23 21:46:40.000000"
        assert alice["last_updated"] == "2025-08-04 11:33:20.000000"

        bob = next(r for r in m.results if r["given_name"] == "Bob")
        assert bob["lid"] is None
        assert bob["disappearing_mode_duration"] is None
        assert bob["disappearing_mode_is_on"] is False
        assert bob["disappearing_mode_label"] == "off"
        assert bob["disappearing_mode_timestamp"] is None

        assert len(m.timeline) == 1
        assert m.timeline[0]["event"] == "disappearing_mode_set"
        assert m.timeline[0]["timestamp"] == "2025-07-23 21:46:40.000000"
        assert "24 hours" in m.timeline[0]["data"]
        assert "14155550100@s.whatsapp.net" in m.timeline[0]["data"]

        assert len(m.alertstore.alerts) == 0

    def test_missing_database(self, tmp_path):
        m = WhatsappContacts(target_path=str(tmp_path))
        run_module(m)
        assert m.results == []
        assert len(m.alertstore.alerts) == 0
