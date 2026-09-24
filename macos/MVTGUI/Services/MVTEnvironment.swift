import Foundation

/// Locates the MVT command-line tools and holds app-wide preferences for
/// running them. Published state is only mutated on the main queue, which is
/// what makes the unchecked Sendable conformance safe.
final class MVTEnvironment: ObservableObject, @unchecked Sendable {
    enum Status: Equatable {
        case unknown
        case checking
        case found(version: String)
        case missing
    }

    @Published private(set) var status: Status = .unknown
    @Published private(set) var binDirectory: URL?
    /// Whether `--verbose` is accepted before the command name. Releases
    /// before 2026.9 only accept it after (e.g. `check-backup --verbose`).
    @Published private(set) var acceptsGlobalVerbose = true
    /// The newest MVT release on PyPI, once looked up.
    @Published private(set) var latestVersion: String?

    var installedVersion: String? {
        if case .found(let version) = status { return version }
        return nil
    }

    /// True when the MVT in use is an older release than the newest on PyPI.
    /// Development builds (from a source checkout) are never flagged.
    var isOutdated: Bool {
        guard let installed = installedVersion, let latest = latestVersion else { return false }
        return Self.isOlder(installed, than: latest)
    }

    /// Whether the MVT in use is the one this app installed.
    var usesManagedInstall: Bool {
        binDirectory?.standardizedFileURL == Self.managedVenv.appendingPathComponent("bin").standardizedFileURL
    }

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

    /// An always-empty MVT data folder. Pointing MVT_DATA_FOLDER at it stops
    /// MVT from loading every downloaded indicator file, so that a check uses
    /// only the files picked for it.
    static var emptyDataFolder: URL {
        applicationSupportDirectory.appendingPathComponent("empty-mvt-data", isDirectory: true)
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
        guard let binDirectory else { return nil }
        let url = binDirectory.appendingPathComponent(tool.rawValue)
        // Releases before the `mvt` command existed offer the same commands
        // (version, download-iocs) on mvt-ios.
        if tool == .common && !FileManager.default.isExecutableFile(atPath: url.path) {
            return binDirectory.appendingPathComponent(MVTTool.ios.rawValue)
        }
        return url
    }

    /// Options accepted by all three scripts before the command name.
    var globalArguments: [String] {
        var args: [String] = []
        if !checkForUpdates { args.append("--disable-update-check") }
        if !checkIndicatorUpdates { args.append("--disable-indicator-update-check") }
        if verbose && acceptsGlobalVerbose { args.append("--verbose") }
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
            var globalVerbose = true
            if let dir = found {
                let (_, help) = Self.capture(dir.appendingPathComponent(MVTTool.ios.rawValue), ["--help"])
                globalVerbose = help.contains("--verbose")
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
                self.acceptsGlobalVerbose = globalVerbose
                if found != nil {
                    self.status = .found(version: version ?? "unknown version")
                } else {
                    self.status = .missing
                }
            }
        }
        Task { await self.lookUpLatestVersion() }
    }

    static let pypiURL = URL(string: "https://pypi.org/pypi/mvt/json")!

    @MainActor
    func lookUpLatestVersion() async {
        var request = URLRequest(url: Self.pypiURL)
        request.timeoutInterval = 15
        guard let (data, _) = try? await URLSession.shared.data(for: request),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let info = json["info"] as? [String: Any],
              let version = info["version"] as? String else { return }
        latestVersion = version
    }

    /// Compares release versions like 2026.5.12 numerically. Returns false for
    /// anything that isn't a plain release (e.g. 0.1.dev148+g777db67).
    static func isOlder(_ installed: String, than latest: String) -> Bool {
        func parts(_ v: String) -> [Int]? {
            let pieces = v.split(separator: ".")
            let numbers = pieces.compactMap { Int($0) }
            return numbers.count == pieces.count && !numbers.isEmpty ? numbers : nil
        }
        guard let a = parts(installed), let b = parts(latest) else { return false }
        for i in 0..<max(a.count, b.count) {
            let x = i < a.count ? a[i] : 0
            let y = i < b.count ? b[i] : 0
            if x != y { return x < y }
        }
        return false
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
