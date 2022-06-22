# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

INTERACTIONC_BACKUP_IDS = [
    "1f5a521220a3ad80ebfdc196978df8e7a2e49dee",
]
INTERACTIONC_ROOT_PATHS = [
    "private/var/mobile/Library/CoreDuet/People/interactionC.db",
]


class InteractionC(IOSExtraction):
    """This module extracts data from InteractionC db."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

        self.timestamps = [
            "start_date",
            "end_date",
            "interactions_creation_date",
            "contacts_creation_date",
            "first_incoming_recipient_date",
            "first_incoming_sender_date",
            "first_outgoing_recipient_date",
            "last_incoming_sender_date",
            "last_incoming_recipient_date",
            "last_outgoing_recipient_date",
        ]

    def serialize(self, record: dict) -> None:
        records = []
        processed = []
        for ts in self.timestamps:
            # Check if the record has the current timestamp.
            if ts not in record or not record[ts]:
                continue

            # Check if the timestamp was already processed.
            if record[ts] in processed:
                continue

            records.append({
                "timestamp": record[ts],
                "module": self.__class__.__name__,
                "event": ts,
                "data": f"[{record['bundle_id']}] {record['account']} - from {record['sender_display_name']} "
                        f"({record['sender_identifier']}) to {record['recipient_display_name']} "
                        f"({record['recipient_identifier']}): {record['content']}"
            })
            processed.append(record[ts])

        return records

    def run(self) -> None:
        self._find_ios_database(backup_ids=INTERACTIONC_BACKUP_IDS,
                                root_paths=INTERACTIONC_ROOT_PATHS)
        self.log.info("Found InteractionC database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()

        # TODO: Support all versions.
        # Taken from:
        # https://github.com/mac4n6/APOLLO/blob/master/modules/interaction_contact_interactions.txt
        cur.execute("""
            SELECT
                ZINTERACTIONS.ZSTARTDATE,
                ZINTERACTIONS.ZENDDATE,
                ZINTERACTIONS.ZBUNDLEID,
                ZINTERACTIONS.ZACCOUNT,
                ZINTERACTIONS.ZTARGETBUNDLEID,
                CASE ZINTERACTIONS.ZDIRECTION
                    WHEN '0' THEN 'INCOMING'
                    WHEN '1' THEN 'OUTGOING'
                END 'DIRECTION',
                ZCONTACTS.ZDISPLAYNAME,
                ZCONTACTS.ZIDENTIFIER,
                ZCONTACTS.ZPERSONID,
                RECEIPIENTCONACT.ZDISPLAYNAME,
                RECEIPIENTCONACT.ZIDENTIFIER,
                RECEIPIENTCONACT.ZPERSONID,
                ZINTERACTIONS.ZRECIPIENTCOUNT,
                ZINTERACTIONS.ZDOMAINIDENTIFIER,
                ZINTERACTIONS.ZISRESPONSE,
                ZATTACHMENT.ZCONTENTTEXT,
                ZATTACHMENT.ZUTI,
                ZATTACHMENT.ZCONTENTURL,
                ZATTACHMENT.ZSIZEINBYTES,
                ZATTACHMENT.ZPHOTOLOCALIDENTIFIER,
                HEX(ZATTACHMENT.ZIDENTIFIER),
                ZATTACHMENT.ZCLOUDIDENTIFIER,
                ZCONTACTS.ZINCOMINGRECIPIENTCOUNT,
                ZCONTACTS.ZINCOMINGSENDERCOUNT,
                ZCONTACTS.ZOUTGOINGRECIPIENTCOUNT,
                ZINTERACTIONS.ZCREATIONDATE,
                ZCONTACTS.ZCREATIONDATE,
                ZCONTACTS.ZFIRSTINCOMINGRECIPIENTDATE,
                ZCONTACTS.ZFIRSTINCOMINGSENDERDATE,
                ZCONTACTS.ZFIRSTOUTGOINGRECIPIENTDATE,
                ZCONTACTS.ZLASTINCOMINGSENDERDATE,
                ZCONTACTS.ZLASTINCOMINGRECIPIENTDATE,
                ZCONTACTS.ZLASTOUTGOINGRECIPIENTDATE,
                ZCONTACTS.ZCUSTOMIDENTIFIER,
                ZINTERACTIONS.ZCONTENTURL,
                ZINTERACTIONS.ZLOCATIONUUID,
                ZINTERACTIONS.ZGROUPNAME,
                ZINTERACTIONS.ZDERIVEDINTENTIDENTIFIER,
                ZINTERACTIONS.Z_PK
            FROM ZINTERACTIONS
                LEFT JOIN ZCONTACTS ON ZINTERACTIONS.ZSENDER = ZCONTACTS.Z_PK
                LEFT JOIN Z_1INTERACTIONS ON ZINTERACTIONS.Z_PK == Z_1INTERACTIONS.Z_3INTERACTIONS
                LEFT JOIN ZATTACHMENT ON Z_1INTERACTIONS.Z_1ATTACHMENTS == ZATTACHMENT.Z_PK
                LEFT JOIN Z_2INTERACTIONRECIPIENT ON ZINTERACTIONS.Z_PK== Z_2INTERACTIONRECIPIENT.Z_3INTERACTIONRECIPIENT
                LEFT JOIN ZCONTACTS RECEIPIENTCONACT ON Z_2INTERACTIONRECIPIENT.Z_2RECIPIENTS== RECEIPIENTCONACT.Z_PK;
        """)
        # names = [description[0] for description in cur.description]

        for row in cur:
            self.results.append({
                "start_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[0])),
                "end_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[1])),
                "bundle_id": row[2],
                "account": row[3],
                "target_bundle_id": row[4],
                "direction": row[5],
                "sender_display_name": row[6],
                "sender_identifier": row[7],
                "sender_personid": row[8],
                "recipient_display_name": row[9],
                "recipient_identifier": row[10],
                "recipient_personid": row[11],
                "recipient_count": row[12],
                "domain_identifier": row[13],
                "is_response": row[14],
                "content": row[15],
                "uti": row[16],
                "content_url": row[17],
                "size": row[18],
                "photo_local_id": row[19],
                "attachment_id": row[20],
                "cloud_id": row[21],
                "incoming_recipient_count": row[22],
                "incoming_sender_count": row[23],
                "outgoing_recipient_count": row[24],
                "interactions_creation_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[25])) if row[25] else None,
                "contacts_creation_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[26])) if row[26] else None,
                "first_incoming_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[27])) if row[27] else None,
                "first_incoming_sender_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[28])) if row[28] else None,
                "first_outgoing_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[29])) if row[29] else None,
                "last_incoming_sender_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[30])) if row[30] else None,
                "last_incoming_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[31])) if row[31] else None,
                "last_outgoing_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(row[32])) if row[32] else None,
                "custom_id": row[33],
                "location_uuid": row[35],
                "group_name": row[36],
                "derivied_intent_id": row[37],
                "table_id": row[38]
            })

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d InteractionC events", len(self.results))
