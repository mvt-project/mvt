import Foundation

/// A fully resolved MVT invocation: which script to run, its arguments, and
/// any extra environment variables (used for secrets so they never show up
/// in the process table).
struct Invocation {
    var tool: MVTTool
    var arguments: [String]
    var environment: [String: String]

    /// A shell-like rendering for display. Secrets live in `environment` and
    /// are shown only by name.
    var displayString: String {
        let env = environment.keys.sorted().map { "\($0)=•••• " }.joined()
        let args = arguments.map(Self.shellQuote).joined(separator: " ")
        return "\(env)\(tool.rawValue) \(args)"
    }

    static func shellQuote(_ value: String) -> String {
        let safe = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_./=:@,+"))
        if !value.isEmpty, value.unicodeScalars.allSatisfy(safe.contains) {
            return value
        }
        return "'" + value.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }
}

/// The editable state behind one command's form. Kept per command so that
/// switching between commands in the sidebar does not lose what was entered.
final class CommandForm: ObservableObject {
    let command: MVTCommand

    @Published var inputPath = ""
    @Published var outputPath = ""
    @Published var iocFiles: [String] = []
    @Published var fast = false
    @Published var hashes = false
    @Published var module = ""
    @Published var timezone = ""
    @Published var password = ""
    @Published var useKeyFile = false
    @Published var keyFilePath = ""
    @Published var destinationPath = ""
    @Published var jobs = 4
    @Published var keyFileOutputPath = ""
    @Published var virusTotal = false
    @Published var virusTotalDelay = 16
    @Published var virusTotalAPIKey = ""

    init(command: MVTCommand) {
        self.command = command
    }

    private func has(_ option: CommandOption) -> Bool {
        command.options.contains(option)
    }

    /// Returns a user-facing problem that prevents running, or nil.
    func validationError(listModulesOnly: Bool = false) -> String? {
        let fm = FileManager.default
        if command.inputKind != .none && !listModulesOnly {
            if inputPath.isEmpty {
                return "Choose the \(command.inputLabel.lowercased()) to analyze."
            }
            if !fm.fileExists(atPath: inputPath) {
                return "The selected \(command.inputLabel.lowercased()) no longer exists."
            }
        }
        if listModulesOnly { return nil }
        if has(.destination) && destinationPath.isEmpty {
            return "Choose a destination folder for the decrypted backup."
        }
        if has(.iosPassword) {
            if useKeyFile && command == .iosDecryptBackup {
                if keyFilePath.isEmpty { return "Choose the key file." }
            } else if password.isEmpty {
                return "Enter the backup password."
            }
        }
        if has(.virusTotal) && virusTotal && virusTotalAPIKey.isEmpty
            && ProcessInfo.processInfo.environment["MVT_VT_API_KEY"] == nil {
            return "Enter a VirusTotal API key, or turn VirusTotal lookups off."
        }
        for ioc in iocFiles where !fm.fileExists(atPath: ioc) {
            return "Indicator file not found: \(ioc)"
        }
        return nil
    }

    func invocation(listModulesOnly: Bool = false) -> Invocation {
        var args: [String] = [command.subcommand]
        var env: [String: String] = [:]

        if listModulesOnly {
            args.append("--list-modules")
            // click requires an existing positional path even when only
            // listing modules; any directory will do.
            if command.inputKind != .none {
                let exists = !inputPath.isEmpty && FileManager.default.fileExists(atPath: inputPath)
                args.append(exists ? inputPath : NSTemporaryDirectory())
            }
            return Invocation(tool: command.tool, arguments: args, environment: env)
        }

        if has(.iocs) {
            for ioc in iocFiles { args += ["--iocs", ioc] }
        }
        if has(.output) && !outputPath.isEmpty {
            args += ["--output", outputPath]
        }
        if has(.fast) && fast { args.append("--fast") }
        if has(.hashes) && hashes { args.append("--hashes") }

        let trimmedModule = module.trimmingCharacters(in: .whitespaces)
        if has(.module) && !trimmedModule.isEmpty {
            args += ["--module", trimmedModule]
        }
        let trimmedTZ = timezone.trimmingCharacters(in: .whitespaces)
        if has(.timezone) && !trimmedTZ.isEmpty {
            args += ["--timezone", trimmedTZ]
        }
        if has(.destination) {
            args += ["--destination", destinationPath, "--jobs", String(jobs)]
        }
        if has(.iosPassword) {
            if useKeyFile && command == .iosDecryptBackup {
                args += ["--key-file", keyFilePath]
            } else {
                env["MVT_IOS_BACKUP_PASSWORD"] = password
            }
        }
        if has(.keyFileOutput) && !keyFileOutputPath.isEmpty {
            args += ["--key-file", keyFileOutputPath]
        }
        if has(.androidPassword) && !password.isEmpty {
            env["MVT_ANDROID_BACKUP_PASSWORD"] = password
        }
        if has(.virusTotal) && virusTotal {
            args += ["--virustotal", "--delay", String(virusTotalDelay)]
            if !virusTotalAPIKey.isEmpty { env["MVT_VT_API_KEY"] = virusTotalAPIKey }
        }
        // The GUI has no terminal to answer prompts on.
        if has(.nonInteractive) { args.append("--non-interactive") }

        if command.inputKind != .none { args.append(inputPath) }

        return Invocation(tool: command.tool, arguments: args, environment: env)
    }
}
