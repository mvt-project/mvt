import Foundation

/// The three console scripts MVT installs (see `[project.scripts]` in pyproject.toml).
enum MVTTool: String {
    case ios = "mvt-ios"
    case android = "mvt-android"
    case common = "mvt"
}

/// What kind of path a command takes as its positional argument.
enum InputKind {
    case folder
    case file
    case fileOrFolder
    case none
}

/// Individual options a command form can expose. Each one maps to a flag of
/// the underlying MVT command, as printed by `<tool> <command> --help`.
/// macos/scripts/check_cli_contract.py verifies these against the CLI in CI;
/// update its EXPECTED_OPTIONS when changing what a command passes.
enum CommandOption: Hashable {
    case iocs            // -i/--iocs PATH (repeatable)
    case output          // -o/--output PATH
    case fast            // -f/--fast
    case hashes          // -H/--hashes
    case module          // -m/--module NAME
    case listModules     // -l/--list-modules
    case timezone        // -t/--timezone TZ
    case iosPassword     // MVT_IOS_BACKUP_PASSWORD, or -k/--key-file
    case androidPassword // MVT_ANDROID_BACKUP_PASSWORD
    case virusTotal      // -V/--virustotal, -d/--delay, MVT_VT_API_KEY
    case destination     // -d/--destination (decrypt-backup)
    case jobs            // --jobs (decrypt-backup)
    case keyFileOutput   // -k/--key-file (extract-key: file to write)
    case nonInteractive  // -n/--non-interactive (always passed)
}

enum MVTCommand: String, CaseIterable, Identifiable, Hashable {
    // iOS
    case iosCheckBackup
    case iosCheckFS
    case iosCheckSysdiagnose
    case iosDecryptBackup
    case iosExtractKey
    case iosCheckIOCs
    // Android
    case androidCheckAndroidQF
    case androidCheckBackup
    case androidCheckBugreport
    case androidCheckIntrusionLogs
    case androidCheckIOCs
    // Common
    case downloadIOCs

    var id: String { rawValue }

    static let iosCommands: [MVTCommand] = [
        .iosCheckBackup, .iosCheckFS, .iosCheckSysdiagnose,
        .iosDecryptBackup, .iosExtractKey, .iosCheckIOCs,
    ]
    static let androidCommands: [MVTCommand] = [
        .androidCheckAndroidQF, .androidCheckBackup, .androidCheckBugreport,
        .androidCheckIntrusionLogs, .androidCheckIOCs,
    ]

    var tool: MVTTool {
        switch self {
        case .iosCheckBackup, .iosCheckFS, .iosCheckSysdiagnose,
             .iosDecryptBackup, .iosExtractKey, .iosCheckIOCs:
            return .ios
        case .androidCheckAndroidQF, .androidCheckBackup, .androidCheckBugreport,
             .androidCheckIntrusionLogs, .androidCheckIOCs:
            return .android
        case .downloadIOCs:
            return .common
        }
    }

    var subcommand: String {
        switch self {
        case .iosCheckBackup: return "check-backup"
        case .iosCheckFS: return "check-fs"
        case .iosCheckSysdiagnose: return "check-sysdiagnose"
        case .iosDecryptBackup: return "decrypt-backup"
        case .iosExtractKey: return "extract-key"
        case .iosCheckIOCs, .androidCheckIOCs: return "check-iocs"
        case .androidCheckAndroidQF: return "check-androidqf"
        case .androidCheckBackup: return "check-backup"
        case .androidCheckBugreport: return "check-bugreport"
        case .androidCheckIntrusionLogs: return "check-intrusion-logs"
        case .downloadIOCs: return "download-iocs"
        }
    }

    var title: String {
        switch self {
        case .iosCheckBackup: return "Check Backup"
        case .iosCheckFS: return "Check Filesystem Dump"
        case .iosCheckSysdiagnose: return "Check Sysdiagnose"
        case .iosDecryptBackup: return "Decrypt Backup"
        case .iosExtractKey: return "Extract Backup Key"
        case .iosCheckIOCs, .androidCheckIOCs: return "Re-check Results"
        case .androidCheckAndroidQF: return "Check AndroidQF"
        case .androidCheckBackup: return "Check Backup (SMS)"
        case .androidCheckBugreport: return "Check Bug Report"
        case .androidCheckIntrusionLogs: return "Check Intrusion Logs"
        case .downloadIOCs: return "Download Indicators"
        }
    }

    var systemImage: String {
        switch self {
        case .iosCheckBackup, .androidCheckBackup: return "externaldrive"
        case .iosCheckFS: return "folder"
        case .iosCheckSysdiagnose: return "stethoscope"
        case .iosDecryptBackup: return "lock.open"
        case .iosExtractKey: return "key"
        case .iosCheckIOCs, .androidCheckIOCs: return "arrow.triangle.2.circlepath"
        case .androidCheckAndroidQF: return "shippingbox"
        case .androidCheckBugreport: return "ladybug"
        case .androidCheckIntrusionLogs: return "shield.lefthalf.filled"
        case .downloadIOCs: return "arrow.down.circle"
        }
    }

    var summary: String {
        switch self {
        case .iosCheckBackup:
            return "Extract artifacts from an iTunes/Finder backup. Encrypted backups must be decrypted first with Decrypt Backup."
        case .iosCheckFS:
            return "Extract artifacts from a full filesystem dump or mount point (e.g. from a jailbroken device)."
        case .iosCheckSysdiagnose:
            return "Analyze an iOS sysdiagnose archive (.tar.gz) or an extracted sysdiagnose folder. Forensic checks come from installed plugin packages."
        case .iosDecryptBackup:
            return "Decrypt an encrypted iTunes/Finder backup into a new folder, using the backup password or a key file."
        case .iosExtractKey:
            return "Derive the decryption key from an encrypted backup and its password, so you can decrypt later without the password. The key is sensitive — keep it safe."
        case .iosCheckIOCs, .androidCheckIOCs:
            return "Compare JSON results from a previous run against indicators, without re-reading the original acquisition."
        case .androidCheckAndroidQF:
            return "Analyze an acquisition collected with AndroidQF (folder or .zip). Includes the nested backup, bug report and intrusion logs when present."
        case .androidCheckBackup:
            return "Check an Android backup (.ab file or unpacked folder). Currently extracts SMS/MMS messages."
        case .androidCheckBugreport:
            return "Analyze a standalone Android bug report (.zip)."
        case .androidCheckIntrusionLogs:
            return "Analyze Android Advanced Protection intrusion logs (folder of .txt files or a .zip)."
        case .downloadIOCs:
            return "Download the public STIX2 indicators from the mvt-indicators repository. Downloaded indicators are used automatically by every check."
        }
    }

    var inputLabel: String {
        switch self {
        case .iosCheckBackup, .iosDecryptBackup, .iosExtractKey: return "Backup folder"
        case .iosCheckFS: return "Filesystem dump"
        case .iosCheckSysdiagnose: return "Sysdiagnose"
        case .iosCheckIOCs, .androidCheckIOCs: return "Results folder"
        case .androidCheckAndroidQF: return "AndroidQF output"
        case .androidCheckBackup: return "Backup"
        case .androidCheckBugreport: return "Bug report"
        case .androidCheckIntrusionLogs: return "Intrusion logs"
        case .downloadIOCs: return ""
        }
    }

    var inputKind: InputKind {
        switch self {
        case .iosCheckBackup, .iosCheckFS, .iosDecryptBackup, .iosExtractKey,
             .iosCheckIOCs, .androidCheckIOCs:
            return .folder
        case .androidCheckBugreport:
            return .file
        case .iosCheckSysdiagnose, .androidCheckAndroidQF, .androidCheckBackup,
             .androidCheckIntrusionLogs:
            return .fileOrFolder
        case .downloadIOCs:
            return .none
        }
    }

    var options: Set<CommandOption> {
        switch self {
        case .iosCheckBackup, .iosCheckFS:
            return [.iocs, .output, .fast, .hashes, .module, .listModules]
        case .iosCheckSysdiagnose:
            return [.iocs, .output, .hashes, .module, .listModules]
        case .iosDecryptBackup:
            return [.destination, .jobs, .iosPassword, .hashes]
        case .iosExtractKey:
            return [.iosPassword, .keyFileOutput]
        case .iosCheckIOCs, .androidCheckIOCs:
            return [.iocs, .module, .listModules]
        case .androidCheckAndroidQF:
            return [.iocs, .output, .hashes, .module, .listModules,
                    .virusTotal, .androidPassword, .nonInteractive]
        case .androidCheckBackup:
            return [.iocs, .output, .listModules, .androidPassword, .nonInteractive]
        case .androidCheckBugreport, .androidCheckIntrusionLogs:
            return [.iocs, .output, .module, .listModules, .timezone]
        case .downloadIOCs:
            return []
        }
    }

    /// Whether the command writes results a user would want to browse afterwards.
    var producesResults: Bool { options.contains(.output) }

    var docsURL: URL {
        let path: String
        switch self {
        case .iosCheckBackup, .iosDecryptBackup, .iosExtractKey: path = "ios/backup/check/"
        case .iosCheckFS: path = "ios/filesystem/check/"
        case .iosCheckSysdiagnose: path = "ios/sysdiagnose/"
        case .iosCheckIOCs, .androidCheckIOCs, .downloadIOCs: path = "iocs/"
        case .androidCheckAndroidQF: path = "android/methodology/"
        case .androidCheckBackup: path = "android/backup/"
        case .androidCheckBugreport: path = "android/adb/"
        case .androidCheckIntrusionLogs: path = "android/intrusion_logs/"
        }
        return URL(string: "https://docs.mvt.re/en/latest/\(path)")!
    }
}
