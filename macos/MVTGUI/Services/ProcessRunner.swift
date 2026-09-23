import Foundation

/// Runs one external process at a time and streams its combined
/// stdout/stderr into `lines` for display. All published state is mutated on
/// the main queue.
final class ProcessRunner: ObservableObject {
    @Published private(set) var lines: [LogLine] = []
    @Published private(set) var isRunning = false
    @Published private(set) var lastExitCode: Int32?
    @Published private(set) var alertCounts: [LogLevel: Int] = [:]
    @Published var title = ""

    /// Keep memory bounded on very chatty runs.
    private let maxLines = 50_000
    private var nextID = 0
    private var process: Process?

    /// Directories GUI apps don't get on their PATH by default but where
    /// Homebrew, pipx and uv put executables.
    static var extraPathDirectories: [String] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        return [
            "\(home)/.local/bin",
            "/opt/homebrew/bin",
            "/usr/local/bin",
        ]
    }

    static func environment(adding extra: [String: String]) -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        let currentPath = env["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin"
        env["PATH"] = (extraPathDirectories + [currentPath]).joined(separator: ":")
        // MVT prints through rich; keep output plain and wide enough that
        // log lines don't wrap mid-message.
        env["NO_COLOR"] = "1"
        env["TERM"] = "dumb"
        env["COLUMNS"] = "200"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        for (key, value) in extra { env[key] = value }
        return env
    }

    func clear() {
        lines.removeAll()
        alertCounts = [:]
        lastExitCode = nil
        nextID = 0
    }

    func appendNote(_ text: String, level: LogLevel = .command) {
        append([(text, level)])
    }

    /// Launches `executable` and returns its exit status once it has finished
    /// and all of its output has been delivered.
    @discardableResult
    func run(
        executable: URL,
        arguments: [String],
        environment extraEnvironment: [String: String] = [:],
        displayCommand: String? = nil
    ) async -> Int32 {
        await withCheckedContinuation { continuation in
            DispatchQueue.main.async {
                self.start(
                    executable: executable,
                    arguments: arguments,
                    extraEnvironment: extraEnvironment,
                    displayCommand: displayCommand
                ) { status in
                    continuation.resume(returning: status)
                }
            }
        }
    }

    private func start(
        executable: URL,
        arguments: [String],
        extraEnvironment: [String: String],
        displayCommand: String?,
        completion: @escaping (Int32) -> Void
    ) {
        guard !isRunning else {
            appendNote("Another task is already running.", level: .error)
            completion(-1)
            return
        }

        let process = Process()
        process.executableURL = executable
        process.arguments = arguments
        process.environment = Self.environment(adding: extraEnvironment)
        process.standardInput = FileHandle.nullDevice

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe

        let shown = displayCommand
            ?? ([executable.path] + arguments).map(Invocation.shellQuote).joined(separator: " ")
        appendNote("$ \(shown)")

        do {
            try process.run()
        } catch {
            appendNote("Could not launch \(executable.path): \(error.localizedDescription)", level: .error)
            lastExitCode = -1
            completion(-1)
            return
        }

        self.process = process
        isRunning = true
        lastExitCode = nil

        let handle = pipe.fileHandleForReading
        Thread.detachNewThread { [weak self] in
            var buffer = Data()
            while true {
                let chunk = handle.availableData
                if chunk.isEmpty { break }
                buffer.append(chunk)
                let complete = Self.takeCompleteLines(from: &buffer)
                if !complete.isEmpty {
                    DispatchQueue.main.async { self?.appendRaw(complete) }
                }
            }
            if !buffer.isEmpty {
                let rest = String(decoding: buffer, as: UTF8.self)
                DispatchQueue.main.async { self?.appendRaw([rest]) }
            }
            process.waitUntilExit()
            let status = process.terminationStatus
            DispatchQueue.main.async {
                guard let self else { return completion(status) }
                self.isRunning = false
                self.process = nil
                self.lastExitCode = status
                if process.terminationReason == .uncaughtSignal {
                    self.appendNote("Stopped.", level: .warning)
                } else if status == 0 {
                    self.appendNote("Finished successfully.")
                } else {
                    self.appendNote("Exited with status \(status).", level: .error)
                }
                completion(status)
            }
        }
    }

    func cancel() {
        guard let process, process.isRunning else { return }
        process.interrupt()
        DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak process] in
            if let process, process.isRunning { process.terminate() }
        }
    }

    // MARK: - Line handling

    private static func takeCompleteLines(from buffer: inout Data) -> [String] {
        var result: [String] = []
        var start = buffer.startIndex
        var index = buffer.startIndex
        while index < buffer.endIndex {
            if buffer[index] == 0x0A {
                var line = String(decoding: buffer[start..<index], as: UTF8.self)
                // A carriage return redraws the line (progress output); keep
                // only what ended up visible.
                if line.contains("\r") {
                    line = line.split(separator: "\r", omittingEmptySubsequences: true)
                        .last.map(String.init) ?? ""
                }
                result.append(line)
                start = buffer.index(after: index)
            }
            index = buffer.index(after: index)
        }
        buffer = Data(buffer[start...])
        return result
    }

    private func appendRaw(_ raw: [String]) {
        append(raw.map { text in
            let clean = ANSI.strip(text)
            return (clean, LogLevel.classify(clean))
        })
    }

    private func append(_ entries: [(String, LogLevel)]) {
        var newLines: [LogLine] = []
        newLines.reserveCapacity(entries.count)
        for (text, level) in entries {
            newLines.append(LogLine(id: nextID, text: text, level: level))
            nextID += 1
            if level.isAlert { alertCounts[level, default: 0] += 1 }
        }
        lines.append(contentsOf: newLines)
        if lines.count > maxLines {
            lines.removeFirst(lines.count - maxLines)
        }
    }
}
