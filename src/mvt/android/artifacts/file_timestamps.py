# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact
from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult


class FileTimestampsArtifact(AndroidArtifact):
    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        records = []

        for ts in set(
            [
                record.get("access_time"),
                record.get("changed_time"),
                record.get("modified_time"),
            ]
        ):
            if not ts:
                continue

            macb = ""
            macb += "M" if ts == record.get("modified_time") else "-"
            macb += "A" if ts == record.get("access_time") else "-"
            macb += "C" if ts == record.get("changed_time") else "-"
            macb += "-"

            msg = record["path"]
            if record.get("context"):
                msg += f" ({record['context']})"

            records.append(
                {
                    "timestamp": ts,
                    "module": self.__class__.__name__,
                    "event": macb,
                    "data": msg,
                }
            )

        return records
