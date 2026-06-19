# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .connect_event import ConnectEvent
from .dns_event import DnsEvent
from .security_event import SecurityEvent

INTRUSION_LOGS_MODULES = [
    DnsEvent,
    ConnectEvent,
    SecurityEvent,
]

KNOWN_INTRUSION_LOG_EVENT_TYPES = {
    "connect_event",
    "dns_event",
    "security_event",
}
