# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .analytics import Analytics
from .cache_files import CacheFiles
from .filesystem import Filesystem
from .net_netusage import Netusage
from .safari_favicon import SafariFavicon
from .shutdownlog import ShutdownLog
from .version_history import IOSVersionHistory
from .webkit_indexeddb import WebkitIndexedDB
from .webkit_localstorage import WebkitLocalStorage
from .webkit_safariviewservice import WebkitSafariViewService

FS_MODULES = [CacheFiles, Filesystem, Netusage, Analytics, SafariFavicon, ShutdownLog,
              IOSVersionHistory, WebkitIndexedDB, WebkitLocalStorage,
              WebkitSafariViewService]
