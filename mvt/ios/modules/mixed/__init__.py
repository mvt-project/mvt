# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .calls import Calls
from .chrome_favicon import ChromeFavicon
from .chrome_history import ChromeHistory
from .contacts import Contacts
from .firefox_favicon import FirefoxFavicon
from .firefox_history import FirefoxHistory
from .idstatuscache import IDStatusCache
from .interactionc import InteractionC
from .locationd import LocationdClients
from .net_datausage import Datausage
from .safari_browserstate import SafariBrowserState
from .safari_history import SafariHistory
from .sms import SMS
from .sms_attachments import SMSAttachments
from .webkit_resource_load_statistics import WebkitResourceLoadStatistics
from .webkit_session_resource_log import WebkitSessionResourceLog
from .whatsapp import Whatsapp

MIXED_MODULES = [Calls, ChromeFavicon, ChromeHistory, Contacts, FirefoxFavicon,
                 FirefoxHistory, IDStatusCache, InteractionC, LocationdClients,
                 Datausage, SafariBrowserState, SafariHistory, SMS, SMSAttachments,
                 WebkitResourceLoadStatistics, WebkitSessionResourceLog, Whatsapp,]
