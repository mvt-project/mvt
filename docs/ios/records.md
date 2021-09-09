# Records extracted by `mvt-ios`

In this page you can find a (reasonably) up-to-date breakdown of the files created by MVT when performing an analysis of logs, backups or filesystem dumps.

## Records extracted by `check-fs` or `check-backup`

### `backup_info.json`

!!! info "Availabiliy"
    Backup: :material-check:  
    Full filesystem dump: :material-close:

This JSON file is created by mvt-ios' `BackupInfo` module. The module extracts some details about the backup and the device, such as name, phone number, IMEI, product type and version.

---

### `cache_files.json`

!!! info "Availability"
    Backup: :material-close:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `CacheFiles` module. The module extracts records from all SQLite database files stored on disk with the name *Cache.db*. These databases typically contain data from iOS' [internal URL caching](https://developer.apple.com/documentation/foundation/nsurlcache). Through this module you might be able to recover records of HTTP requests and responses performed my applications as well as system services, that would otherwise be unavailable. For example, you might see HTTP requests part of an exploitation chain performed by an iOS service attempting to download a first stage malicious payload.

If indicators are provided through the command-line, they are checked against the requested URL. Any matches are stored in *cache_files_detected.json*.

---

### `calls.json`

!!! info "Availability"
    Backup (if encrypted): :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `Calls` module. The module extracts records from a SQLite database located at */private/var/mobile/Library/CallHistoryDB/CallHistory.storedata*, which contains records of incoming and outgoing calls, including from messaging apps such as WhatsApp or Skype.

---

### `chrome_favicon.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `ChromeFavicon` module. The module extracts records from a SQLite database located at */private/var/mobile/Containers/Data/Application/\*/Library/Application Support/Google/Chrome/Default/Favicons*, which contains a mapping of favicons' URLs and the visited URLs which loaded them.

If indicators are provided through the command-line, they are checked against both the favicon URL and the visited URL. Any matches are stored in *chrome_favicon_detected.json*.

---

### `chrome_history.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `ChromeHistory` module. The module extracts records from a SQLite database located at */private/var/mobile/Containers/Data/Application/\*/Library/Application Support/Google/Chrome/Default/History*, which contains a history of URL visits.

If indicators a provided through the command-line, they are checked against the visited URL. Any matches are stored in *chrome_history_detected.json*.

---

### `configuration_profiles.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-close:

This JSON file is created by mvt-ios' `ConfigurationProfiles` module. The module extracts details about iOS configuration profiles that have been installed on the device. These should include both default iOS as well as third-party profiles.

---

### `contacts.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `Contacts` module. The module extracts records from a SQLite database located at */private/var/mobile/Library/AddressBook/AddressBook.sqlitedb*, which contains records from the phone's address book. While this database obviously would not contain any malicious indicators per se, you might want to use it to compare records from other apps (such as iMessage, SMS, etc.) to filter those originating from unknown origins.

---

### `firefox_favicon.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `FirefoxFavicon` module. The module extracts records from a SQLite database located at */private/var/mobile/profile.profile/browser.db*, which contains a mapping of favicons' URLs and the visited URLs which loaded them.

If indicators are provided through the command-line, they are checked against both the favicon URL and the visited URL. Any matches are stored in *firefox_favicon_detected.json*.

---

### `firefox_history.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `FirefoxHistory` module. The module extracts records from a SQLite database located at */private/var/mobile/profile.profile/browser.db*, which contains a history of URL visits.

If indicators a provided through the command-line, they are checked against the visited URL. Any matches are stored in *firefox_history_detected.json*.

---

### `id_status_cache.json`

!!! info "Availability"
    Backup (before iOS 14.7): :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `IDStatusCache` module. The module extracts records from a plist file located at */private/var/mobile/Library/Preferences/com.apple.identityservices.idstatuscache.plist*, which contains a cache of Apple user ID authentication. This chance will indicate when apps like Facetime and iMessage first established contacts with other registered Apple IDs. This is significant because it might contain traces of malicious accounts involved in exploitation of those apps.

Starting from iOS 14.7.0, this file is empty or absent.

---

### `interaction_c.json`

!!! info "Availability"
    Backup (if encrypted): :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `InteractionC` module. The module extracts records from a SQLite database located at */private/var/mobile/Library/CoreDuet/People/interactionC.db*, which contains details about user interactions with installed apps.

---

### `locationd_clients.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `LocationdClients` module. The module extracts records from a plist file located at */private/var/mobile/Library/Caches/locationd/clients.plist*, which contains a cache of apps which requested access to location services.

---

### `manifest.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-close:

This JSON file is created by mvt-ios' `Manifest` module. The module extracts records from the SQLite database *Manifest.db* contained in iTunes backups, and which indexes the locally backed-up files to the original paths on the iOS device.

If indicators are provided through the command-line, they are checked against the original relative path in case. In some cases, there might be records of files created containing a domain name in their name, for example in the case of browser cache folders. Any matches are stored in *manifest_detected.json*.

---

### `os_analytics_ad_daily.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `OSAnalyticsADDaily` module. The module extracts records from a plist located *private/var/mobile/Library/Preferences/com.apple.osanalytics.addaily.plist*, which contains a history of data usage by processes running on the system. Besides the network statistics, these records are particularly important because they might show traces of malicious process executions and the relevant timeframe.

If indicators are provided through the command-line, they are checked against the process names. Any matches are stored in *os_analytics_ad_daily_detected.json*.

---

### `datausage.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `Datausage` module. The module extracts records from a SQLite database located */private/var/wireless/Library/Databases/DataUsage.sqlite*, which contains a history of data usage by processes running on the system. Besides the network statistics, these records are particularly important because they might show traces of malicious process executions and the relevant timeframe. In particular, processes which do not have a valid bundle ID might require particular attention.

If indicators are provided through the command-line, they are checked against the process names. Any matches are stored in *datausage_detected.json*. If running on a full filesystem dump and if the `--fast` flag was not enabled by command-line, mvt-ios will highlight processes which look suspicious and check the presence of a binary file of the same name in the dump.

---

### `netusage.json`

!!! info "Availability"
    Backup: :material-close:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `Netusage` module. The module extracts records from a SQLite database located */private/var/networkd/netusage.sqlite*, which contains a history of data usage by processes running on the system. Besides the network statistics, these records are particularly important because they might show traces of malicious process executions and the relevant timeframe. In particular, processes which do not have a valid bundle ID might require particular attention.

If indicators are provided through the command-line, they are checked against the process names. Any matches are stored in *netusage_detected.json*. If running on a full filesystem dump and if the `--fast` flag was not enabled by command-line, mvt-ios will highlight processes which look suspicious and check the presence of a binary file of the same name in the dump.

---

### `profile_events.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-close:

This JSON file is created by mvt-ios' `ProfileEvents` module. The module extracts a timeline of configuration profile operations. For example, it should indicate when a new profile was installed from the Settings app, or when one was removed.

---

### `safari_browser_state.json`

!!! info "Availability"
    Backup (if encrypted): :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `SafariBrowserState` module. The module extracts records from the SQLite databases located at */private/var/mobile/Library/Safari/BrowserState.db* or */private/var/mobile/Containers/Data/Application/\*/Library/Safari/BrowserState.db*, which contain records of opened tabs.

If indicators a provided through the command-line, they are checked against the visited URL. Any matches are stored in *safari_browser_state_detected.json*.

---

### `safari_favicon.json`

!!! info "Availability"
    Backup: :material-close:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `SafariFavicon` module. The module extracts records from the SQLite databases located at */private/var/mobile/Library/Image Cache/Favicons/Favicons.db* or */private/var/mobile/Containers/Data/Application/\*/Library/Image Cache/Favicons/Favicons.db*, which contain mappings of favicons' URLs and the visited URLs which loaded them.

If indicators are provided through the command-line, they are checked against both the favicon URL and the visited URL. Any matches are stored in *safari_favicon_detected.json*.

---

### `safari_history.json`

!!! info "Availability"
    Backup (if encrypted): :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `SafariHistory` module. The module extracts records from the SQLite databases located at */private/var/mobile/Library/Safari/History.db* or */private/var/mobile/Containers/Data/Application/\*/Library/Safari/History.db*, which contain a history of URL visits.

If indicators are provided through the command-line, they are checked against the visited URL. Any matches are stored in *safari_history_detected.json*.

---

### `sms.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `SMS` module. The module extracts a list of SMS messages containing HTTP links from the SQLite database located at */private/var/mobile/Library/SMS/sms.db*.

If indicators are provided through the command-line, they are checked against the extracted HTTP links. Any matches are stored in *sms_detected.json*.

---

### `sms_attachments.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `SMSAttachments` module. The module extracts details about attachments sent via SMS or iMessage from the same database used by the `SMS` module. These records might be useful to indicate unique patterns that might be indicative of exploitation attempts leveraging potential vulnerabilities in file format parsers or other forms of file handling by the Messages app.

---

### `tcc.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `TCC` module. The module extracts records from a SQLite database located at */private/var/mobile/Library/TCC/TCC.db*, which contains a list of which services such as microphone, camera, or location, apps have been granted or denied access to.

---

### `version_history.json`

!!! info "Availability"
    Backup: :material-close:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `IOSVersionHistory` module. The module extracts records of iOS software updates from analytics plist files located at */private/var/db/analyticsd/Analytics-Journal-\*.ips*.

---

### `webkit_indexeddb.json`

!!! info "Availability"
    Backup: :material-close:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `WebkitIndexedDB` module. The module extracts a list of file and folder names located at the following path */private/var/mobile/Containers/Data/Application/\*/Library/WebKit/WebsiteData/IndexedDB*, which contains IndexedDB files created by any app installed on the device.

If indicators are provided through the command-line, they are checked against the extracted names. Any matches are stored in *webkit_indexeddb_detected.json*.

---

### `webkit_local_storage.json`

!!! info "Availability"
    Backup: :material-close:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `WebkitLocalStorage` module. The module extracts a list of file and folder names located at the following path */private/var/mobile/Containers/Data/Application/\*/Library/WebKit/WebsiteData/LocalStorage/*, which contains local storage files created by any app installed on the device.

If indicators are provided through the command-line, they are checked against the extracted names. Any matches are stored in *webkit_local_storage_detected.json*.

---

### `webkit_resource_load_statistics.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios `WebkitResourceLoadStatistics` module. The module extracts records from available WebKit ResourceLoadStatistics *observations.db* SQLite3 databases. These records should indicate domain names contacted by apps, including a timestamp.

If indicators are provided through the command-line, they are checked against the extracted domain names. Any matches are stored in *webkit_resource_load_statistics_detected.json*.

---

### `webkit_safari_view_service.json`

!!! info "Availability"
    Backup: :material-close:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `WebkitSafariViewService` module. The module extracts a list of file and folder names located at the following path */private/var/mobile/Containers/Data/Application/\*/SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/*, which contains files cached by SafariVewService.

If indicators are provided through the command-line, they are checked against the extracted names. Any matches are stored in *webkit_safari_view_service_detected.json*.

---

### `webkit_session_resource_log.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `WebkitSessionResourceLog` module. The module extracts records from plist files with the name *full_browsing_session_resourceLog.plist*, which contain records of resources loaded by different domains visited.

If indicators are provided through the command-line, they are checked against the extract domains. Any matches are stored in *webkit_session_resource_log_detected.json*.

---

### `whatsapp.json`

!!! info "Availability"
    Backup: :material-check:  
    Full filesystem dump: :material-check:

This JSON file is created by mvt-ios' `WhatsApp` module. The module extracts a list of WhatsApp messages containing HTTP links from the SQLite database located at *private/var/mobile/Containers/Shared/AppGroup/\*/ChatStorage.sqlite*.

If indicators are provided through the command-line, they are checked against the extracted HTTP links. Any matches are stored in *whatsapp_detected.json*.

