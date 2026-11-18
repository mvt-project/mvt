# Coruna and DarkSword artifacts

The Manifest and Filesystem modules flag two scoped Coruna path patterns without requiring an IOC file:

- `com.apple.<16 hexadecimal characters>.plist` in the mobile user's `Library/Preferences` directory (the `HomeDomain` equivalent in a backup).
- `Documents/.devcache` at the root of an application data container (`AppDomain-<bundle ID>` in a backup).

Path-only matches produce medium-severity alerts. When file contents are available, the modules read at most 1 MiB and check the structures published in [iVerify's September 2026 report](https://www.iverify.com/blog/proliferation-of-coruna-and-darksword). A photo-tracking plist must contain a DCIM path and a positive finite processing timestamp. A device cache must identify `exp` as `plasma` and contain nonempty `ecid`, `gci`, and `unique-id` strings. Matching structures produce high-severity alerts. Matching device identifiers in distinct application containers produce an additional correlation alert. Results retain a fingerprint for correlation instead of raw device identifiers or the tracked photo path.

File content checks accept binary/XML plists and JSON. Missing, malformed or oversized content does not erase a path finding. A path finding alone is not confirmation of compromise. The checks do not inspect arbitrary plists based solely on field names, or flag `.devcache` outside the documented application-container location.

Backup domains with known fixed roots are mapped to device paths for IOC matching. Application container UUIDs are not invented from bundle IDs. iOS path comparisons handle `/var` versus `/private/var`, `/tmp` versus `/private/tmp`, and host path separators. File path indicators match the exact path or descendants at a directory boundary, not similarly prefixed sibling names.

For payload hashes, pass `--hashes` to `check-fs` or `check-backup` (or enable `HASH_FILES` in the configuration). The Filesystem and Manifest modules then store SHA-256 values and compare them with loaded hash IOCs; the saved module results can also be rechecked later. This reads available file contents and increases processing time. Acquisition integrity hashes in `info.json` remain available as before. Reads for artifact inspection and these module hashes are confined to regular files inside the acquisition; symlinks are not followed.

Decrypt encrypted backups before analysis. Sysdiagnose and filesystem metadata may expose paths without the corresponding file bytes, and absence from a partial acquisition does not establish absence from the device. Changes to payload bytes defeat exact hash matching; source-level sample names and legitimate injected process names are not standalone malware indicators.
