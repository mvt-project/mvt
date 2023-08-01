# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.viber import Viber

from ..utils import get_ios_backup_folder


class TestViberModule:

    """This module performs unit and integration tests of the Viber class."""

    # UNIT TESTS

    def test_connect_to_database_nonvalid(self):
        # This file does not exist
        db_file = "/non/existent/file"
        m = Viber(file_path=db_file, target_path=get_ios_backup_folder())

        # Function should fail with DatabaseNotFoundError
        try:
            m.connect_to_database()
        except Exception:
            pass
        else:
            assert False

    def test_connect_to_database_valid(self):
        # This file is valid and does exist
        db_file = (
            "tests/artifacts/ios_backup/83/83b9310399a905c7781f95580174f321cd18fd97"
        )
        m = Viber(target_path=get_ios_backup_folder())
        m.file_path = db_file

        m.connect_to_database()

        # Verify the database connection and cursor was set
        assert m.conn
        assert m.cur

    def test_query_messages_invalid(self):
        # This database is missing the ZVIBERMESSAGE table that is needed for the query
        db_file = "tests/artifacts/viber-database_test_no_table.sqlite"
        m = Viber(target_path=get_ios_backup_folder())
        m.file_path = db_file

        m.connect_to_database()

        # Function should fail because table that is queried doesn't exist
        try:
            m.query_messages()
        except Exception:
            pass
        else:
            assert False

    def test_query_messages_valid(self):
        # This database contains all the tables/columns we expect
        db_file = (
            "tests/artifacts/ios_backup/83/83b9310399a905c7781f95580174f321cd18fd97"
        )
        m = Viber(target_path=get_ios_backup_folder())
        m.file_path = db_file

        m.connect_to_database()

        m.query_messages()

        # Verify the columns we care about were queried
        assert "ZTEXT" in m.col_names
        assert "ZCLIENTMETADATA" in m.col_names
        assert "ZDATE" in m.col_names
        assert "ZPHONE" in m.col_names

    def test_extract_messages_has_expected_results(self):
        db_file = (
            "tests/artifacts/ios_backup/83/83b9310399a905c7781f95580174f321cd18fd97"
        )
        m = Viber(target_path=get_ios_backup_folder())
        m.file_path = db_file

        m.connect_to_database()

        m.query_messages()

        m.extract_messages()

        # Verify the results list is of the length we expect and that each dict element
        # within the list contains the keys we expect
        assert len(m.results) == 2
        assert "isodate" in m.results[0]
        assert "isodate" in m.results[1]
        assert "links" in m.results[1]

    def test_filter_out_trusted_links_internal(self):
        # These links contain the official viber domain so they should be filtered out
        message_links = ["https://www.viber.com/en/", "https://hello.hi.viber.com/"]

        m = Viber(target_path=get_ios_backup_folder())
        m.filter_out_trusted_links(message_links=message_links)

        # Once we filter out the internal links, this list should be empty
        assert len(m.filtered_links) == 0

    def test_filter_out_trusted_links_not_internal(self):
        # These links should not be filtered out as they are not internal viber links
        message_links = ["https://testing.test.com/", "https://not.internal.net/"]

        m = Viber(target_path=get_ios_backup_folder())
        m.filter_out_trusted_links(message_links=message_links)

        # Once we filter out internal links, this list should still have two elements
        assert len(m.filtered_links) == 2

    # INTEGRATION TESTS

    def test_viber(self):
        m = Viber(target_path=get_ios_backup_folder())

        run_module(m)

        # Verify that we are getting the expected number of results and timelines
        # for the test database
        assert len(m.results) == 2
        assert len(m.timeline) == 2  # Viber received and read events.
        assert len(m.detected) == 0

    def test_detection(self):
        indicator_file = "tests/artifacts/pegasus.stix2"
        m = Viber(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        m.indicators = ind

        run_module(m)

        # Verify that we are getting the expected number of detections
        # for the test database
        assert len(m.detected) == 1
