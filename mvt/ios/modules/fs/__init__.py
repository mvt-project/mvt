# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .cache_files import CacheFiles
from .calls import Calls
from .chrome_favicon import ChromeFavicon
from .chrome_history import ChromeHistory
from .contacts import Contacts
from .device_info import DeviceInfo
from .filesystem import Filesystem
from .firefox_favicon import FirefoxFavicon
from .firefox_history import FirefoxHistory
from .idstatuscache import IDStatusCache
from .interactionc import InteractionC
from .locationd import LocationdClients
from .manifest import Manifest
from .net_datausage import Datausage
from .net_netusage import Netusage
from .safari_browserstate import SafariBrowserState
from .safari_favicon import SafariFavicon
from .safari_history import SafariHistory
from .sms import SMS
from .sms_attachments import SMSAttachments
from .version_history import IOSVersionHistory
from .webkit_indexeddb import WebkitIndexedDB
from .webkit_localstorage import WebkitLocalStorage
from .webkit_resource_load_statistics import WebkitResourceLoadStatistics
from .webkit_safariviewservice import WebkitSafariViewService
from .webkit_session_resource_log import WebkitSessionResourceLog
from .whatsapp import Whatsapp

BACKUP_MODULES = [SafariBrowserState, SafariHistory, Datausage, SMS, SMSAttachments,
                  ChromeHistory, ChromeFavicon, WebkitSessionResourceLog,
                  WebkitResourceLoadStatistics, Calls, IDStatusCache, LocationdClients,
                  InteractionC, FirefoxHistory, FirefoxFavicon, Contacts, Manifest, Whatsapp,
                  DeviceInfo]

FS_MODULES = [IOSVersionHistory, SafariHistory, SafariFavicon, SafariBrowserState,
              WebkitIndexedDB, WebkitLocalStorage, WebkitSafariViewService,
              WebkitResourceLoadStatistics, WebkitSessionResourceLog,
              Datausage, Netusage, ChromeHistory,
              ChromeFavicon, Calls, IDStatusCache, SMS, SMSAttachments,
              LocationdClients, InteractionC, FirefoxHistory, FirefoxFavicon,
              Contacts, CacheFiles, Whatsapp, Filesystem]
