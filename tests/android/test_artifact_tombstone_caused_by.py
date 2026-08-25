# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""A `Caused by:` line must not discard the whole text tombstone.

Keys are matched as bare prefixes, so `Caused by: …` — an ordinary line inside
an abort message — reached the `Cause` key, failed the key comparison and
raised, which `Tombstones.run()` logged while dropping the entire crash record.
Seen on a 1.6 MB tombstone whose protobuf twin was zero bytes: the crash then
had no representation at all.
"""

import datetime

from mvt.android.artifacts.tombstone_crashes import TombstoneCrashArtifact

TOMBSTONE = b"""\
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***
Build fingerprint: 'Xiaomi/vili_eea/vili:13/TKQ1.220829.002/V14.0.10.0:user/release-keys'
Revision: '0'
ABI: 'arm64'
Timestamp: 2023-08-24 14:54:47.999124034+0300
Process uptime: 12199s
Cmdline: com.example.game
pid: 8044, tid: 26222, name: UnityMain  >>> com.example.game <<<
uid: 10235
signal 6 (SIGABRT), code -1 (SI_QUEUE), fault addr --------
Abort message: 'No pending exception expected: java.lang.SecurityException: listen
  at void android.os.Parcel.readException() (Parcel.java:2920)
Caused by: android.os.RemoteException: Remote stack trace:
\tat com.android.server.TelephonyRegistry.listen(TelephonyRegistry.java:1096)
"""

WITH_CAUSE = TOMBSTONE + b"Cause: null pointer dereference\n"


class TestTombstoneCausedBy:
    def _parse(self, content):
        artifact = TombstoneCrashArtifact()
        artifact.results = []
        artifact.parse("tombstone_23", datetime.datetime(2023, 8, 24), content)
        return artifact.results

    def test_caused_by_line_does_not_discard_the_tombstone(self):
        results = self._parse(TOMBSTONE)
        assert len(results) == 1
        assert results[0]["pid"] == 8044
        assert results[0]["process_name"] == "UnityMain"
        assert results[0]["uid"] == 10235

    def test_the_real_cause_key_is_still_parsed(self):
        results = self._parse(WITH_CAUSE)
        assert results[0]["cause"] == "null pointer dereference"
