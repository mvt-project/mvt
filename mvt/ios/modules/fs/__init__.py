# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

from .manifest import Manifest
from .contacts import Contacts
from .net_netusage import Netusage
from .net_datausage import Datausage
from .safari_history import SafariHistory
from .safari_favicon import SafariFavicon
from .safari_browserstate import SafariBrowserState
from .webkit_indexeddb import WebkitIndexedDB
from .webkit_localstorage import WebkitLocalStorage
from .webkit_safariviewservice import WebkitSafariViewService
from .webkit_session_resource_log import WebkitSessionResourceLog
from .webkit_resource_load_statistics import WebkitResourceLoadStatistics
from .chrome_history import ChromeHistory
from .chrome_favicon import ChromeFavicon
from .firefox_history import FirefoxHistory
from .firefox_favicon import FirefoxFavicon
from .version_history import IOSVersionHistory
from .idstatuscache import IDStatusCache
from .locationd import LocationdClients
from .interactionc import InteractionC
from .sms import SMS
from .sms_attachments import SMSAttachments
from .calls import Calls
from .whatsapp import Whatsapp
from .cache_files import CacheFiles
from .filesystem import Filesystem

BACKUP_MODULES = [SafariBrowserState, SafariHistory, Datausage, SMS, SMSAttachments,
                  ChromeHistory, ChromeFavicon, WebkitSessionResourceLog,
                  WebkitResourceLoadStatistics, Calls, IDStatusCache, LocationdClients,
                  InteractionC, FirefoxHistory, FirefoxFavicon, Contacts, Manifest, Whatsapp]

FS_MODULES = [IOSVersionHistory, SafariHistory, SafariFavicon, SafariBrowserState,
              WebkitIndexedDB, WebkitLocalStorage, WebkitSafariViewService,
              WebkitResourceLoadStatistics, WebkitSessionResourceLog,
              Datausage, Netusage, ChromeHistory,
              ChromeFavicon, Calls, IDStatusCache, SMS, SMSAttachments,
              LocationdClients, InteractionC, FirefoxHistory, FirefoxFavicon,
              Contacts, CacheFiles, Whatsapp, Filesystem]
