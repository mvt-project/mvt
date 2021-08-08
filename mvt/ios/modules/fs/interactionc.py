# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3
from base64 import b64encode

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from .base import IOSExtraction

INTERACTIONC_BACKUP_IDS = [
    "1f5a521220a3ad80ebfdc196978df8e7a2e49dee",
]
INTERACTIONC_ROOT_PATHS = [
    "private/var/mobile/Library/CoreDuet/People/interactionC.db",
]

class InteractionC(IOSExtraction):
    """This module extracts data from InteractionC db."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
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

    def serialize(self, record):
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
                "data": f"[{record['bundle_id']}] {record['account']} - from {record['sender_display_name']} " \
                        f"({record['sender_identifier']}) to {record['recipient_display_name']} " \
                        f"({record['recipient_identifier']}): {record['content']}"
            })
            processed.append(record[ts])

        return records

    def run(self):
        self._find_ios_database(backup_ids=INTERACTIONC_BACKUP_IDS, root_paths=INTERACTIONC_ROOT_PATHS)
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
        names = [description[0] for description in cur.description]

        for item in cur:
            self.results.append({
                "start_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[0])),
                "end_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[1])),
                "bundle_id": item[2],
                "account": item[3],
                "target_bundle_id": item[4],
                "direction": item[5],
                "sender_display_name": item[6],
                "sender_identifier": item[7],
                "sender_personid": item[8],
                "recipient_display_name": item[9],
                "recipient_identifier": item[10],
                "recipient_personid": item[11],
                "recipient_count": item[12],
                "domain_identifier": item[13],
                "is_response": item[14],
                "content": item[15],
                "uti": item[16],
                "content_url": item[17],
                "size": item[18],
                "photo_local_id": item[19],
                "attachment_id": item[20],
                "cloud_id": item[21],
                "incoming_recipient_count": item[22],
                "incoming_sender_count": item[23],
                "outgoing_recipient_count": item[24],
                "interactions_creation_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[25])) if item[25] else None,
                "contacts_creation_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[26])) if item[26] else None,
                "first_incoming_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[27])) if item[27] else None,
                "first_incoming_sender_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[28])) if item[28] else None,
                "first_outgoing_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[29])) if item[29] else None,
                "last_incoming_sender_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[30])) if item[30] else None,
                "last_incoming_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[31])) if item[31] else None,
                "last_outgoing_recipient_date": convert_timestamp_to_iso(convert_mactime_to_unix(item[32])) if item[32] else None,
                "custom_id": item[33],
                "location_uuid": item[35],
                "group_name": item[36],
                "derivied_intent_id": item[37],
                "table_id": item[38]
            })

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d InteractionC events", len(self.results))
