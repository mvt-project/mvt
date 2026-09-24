import Foundation

/// Locates the MVT command-line tools and holds app-wide preferences for
/// running them.
final class MVTEnvironment: ObservableObject {
    enum Status: Equatable {
        case unknown
        case checking
        case found(version: String)
        case missing
    }

    @Published private(set) var status: Status = .unknown
    @Published private(set) var binDirectory: URL?

    @Published var customBinDirectory: String {
        didSet { defaults.set(customBinDirectory, forKey: Keys.customBinDirectory) }
    }
    @Published var checkForUpdates: Bool {
        didSet { defaults.set(checkForUpdates, forKey: Keys.checkForUpdates) }
    }
    @Published var checkIndicatorUpdates: Bool {
        didSet { defaults.set(checkIndicatorUpdates, forKey: Keys.checkIndicatorUpdates) }
    }
    @Published var verbose: Bool {
        didSet { defaults.set(verbose, forKey: Keys.verbose) }
    }

    private let defaults = UserDefaults.standard

    private enum Keys {
        static let customBinDirectory = "customBinDirectory"
        static let checkForUpdates = "checkForUpdates"
        static let checkIndicatorUpdates = "checkIndicatorUpdates"
        static let verbose = "verbose"
    }

    init() {
        let defaults = UserDefaults.standard
        defaults.register(defaults: [
            Keys.checkForUpdates: true,
            Keys.checkIndicatorUpdates: true,
            Keys.verbose: false,
        ])
        customBinDirectory = defaults.string(forKey: Keys.customBinDirectory) ?? ""
        checkForUpdates = defaults.bool(forKey: Keys.checkForUpdates)
        checkIndicatorUpdates = defaults.bool(forKey: Keys.checkIndicatorUpdates)
        verbose = defaults.bool(forKey: Keys.verbose)
    }

    // MARK: - Paths

    static var applicationSupportDirectory: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("MVT GUI", isDirectory: true)
    }

    /// Virtual environment the Setup screen installs MVT into.
    static var managedVenv: URL {
        applicationSupportDirectory.appendingPathComponent("venv", isDirectory: true)
    }

    /// Where `mvt download-iocs` stores indicators (appdirs' user_data_dir on macOS).
    static var indicatorsDirectory: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("mvt/indicators", isDirectory: true)
    }

    private func candidateDirectories() -> [URL] {
        var dirs: [URL] = []
        let custom = customBinDirectory.trimmingCharacters(in: .whitespaces)
        if !custom.isEmpty {
            dirs.append(URL(fileURLWithPath: (custom as NSString).expandingTildeInPath))
        }
        dirs.append(Self.managedVenv.appendingPathComponent("bin"))
        dirs += ProcessRunner.extraPathDirectories.map { URL(fileURLWithPath: $0) }
        return dirs
    }

    private static func containsTools(_ dir: URL) -> Bool {
        let fm = FileManager.default
        return [MVTTool.ios, .android].allSatisfy {
            fm.isExecutableFile(atPath: dir.appendingPathComponent($0.rawValue).path)
        }
    }

    func executableURL(for tool: MVTTool) -> URL? {
        binDirectory?.appendingPathComponent(tool.rawValue)
    }

    /// Options accepted by all three scripts before the command name.
    var globalArguments: [String] {
        var args: [String] = []
        if !checkForUpdates { args.append("--disable-update-check") }
        if !checkIndicatorUpdates { args.append("--disable-indicator-update-check") }
        if verbose { args.append("--verbose") }
        return args
    }

    // MARK: - Detection

    func refresh() {
        status = .checking
        let candidates = candidateDirectories()
        DispatchQueue.global(qos: .userInitiated).async {
            var found = candidates.first(where: Self.containsTools)
            if found == nil,
               let path = Self.loginShellLookup("mvt-ios") {
                let dir = URL(fileURLWithPath: path).deletingLastPathComponent()
                if Self.containsTools(dir) { found = dir }
            }

            var version: String?
            if let dir = found {
                let exe = dir.appendingPathComponent(MVTTool.ios.rawValue)
                let (_, output) = Self.capture(
                    exe,
                    ["--disable-update-check", "--disable-indicator-update-check", "version"]
                )
                version = output
                    .components(separatedBy: .newlines)
                    .compactMap { line -> String? in
                        let trimmed = line.trimmingCharacters(in: .whitespaces)
                        guard trimmed.hasPrefix("Version:") else { return nil }
                        return trimmed.dropFirst("Version:".count)
                            .trimmingCharacters(in: .whitespaces)
                    }
                    .first
            }

            DispatchQueue.main.async {
                self.binDirectory = found
                if found != nil {
                    self.status = .found(version: version ?? "unknown version")
                } else {
                    self.status = .missing
                }
            }
        }
    }

    // MARK: - Helpers

    /// Finds an executable using the user's login shell, which picks up PATH
    /// changes from ~/.zprofile etc. that GUI apps don't inherit.
    static func loginShellLookup(_ name: String) -> String? {
        let shell = ProcessInfo.processInfo.environment["SHELL"] ?? "/bin/zsh"
        let (status, output) = capture(
            URL(fileURLWithPath: shell),
            ["-l", "-c", "command -v \(name)"],
            timeout: 10
        )
        guard status == 0 else { return nil }
        let path = output.components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .last(where: { $0.hasPrefix("/") })
        return path
    }

    /// Runs a short-lived command synchronously and returns its status and
    /// combined output. Call off the main thread.
    static func capture(_ executable: URL, _ arguments: [String], timeout: TimeInterval = 60) -> (Int32, String) {
        let process = Process()
        process.executableURL = executable
        process.arguments = arguments
        process.environment = ProcessRunner.environment(adding: [:])
        process.standardInput = FileHandle.nullDevice
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
        } catch {
            return (-1, error.localizedDescription)
        }
        let deadline = DispatchTime.now() + timeout
        DispatchQueue.global().asyncAfter(deadline: deadline) {
            if process.isRunning { process.terminate() }
        }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        return (process.terminationStatus, ANSI.strip(String(decoding: data, as: UTF8.self)))
    }

    /// Returns a Python 3.10+ interpreter suitable for creating a virtualenv.
    static func findPython() -> (url: URL, version: String)? {
        var candidates = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
        ]
        if let fromShell = loginShellLookup("python3") { candidates.insert(fromShell, at: 0) }
        candidates.append("/usr/bin/python3")

        var seen = Set<String>()
        for path in candidates where seen.insert(path).inserted {
            guard FileManager.default.isExecutableFile(atPath: path) else { continue }
            let (status, output) = capture(
                URL(fileURLWithPath: path),
                ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                timeout: 30
            )
            let version = output.trimmingCharacters(in: .whitespacesAndNewlines)
            let parts = version.split(separator: ".").compactMap { Int($0) }
            if status == 0, parts.count == 2, parts[0] == 3, parts[1] >= 10 {
                return (URL(fileURLWithPath: path), version)
            }
        }
        return nil
    }
}
