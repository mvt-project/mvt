import Foundation

enum SidebarItem: Hashable {
    case setup
    case results
    case indicators
    case command(MVTCommand)
}

final class AppState: ObservableObject {
    @Published var selection: SidebarItem? = .setup
    @Published var resultsFolder = ""

    /// A single runner: MVT jobs are run one at a time.
    let runner = ProcessRunner()

    private var forms: [MVTCommand: CommandForm] = [:]

    func form(for command: MVTCommand) -> CommandForm {
        if let form = forms[command] { return form }
        let form = CommandForm(command: command)
        forms[command] = form
        return form
    }

    /// Runs an MVT invocation with the app-wide options, replacing whatever
    /// the console showed before.
    @MainActor
    @discardableResult
    func run(_ invocation: Invocation, title: String, environment: MVTEnvironment) async -> Int32 {
        // Never clear the output of a job that is still running.
        guard !runner.isRunning else { return -1 }
        runner.clear()
        runner.title = title
        guard let executable = environment.executableURL(for: invocation.tool) else {
            runner.appendNote(
                "MVT was not found. Install it from the Setup screen or set its location in Settings.",
                level: .error
            )
            return -1
        }
        var globalArgs = environment.globalArguments
        var extraEnvironment = invocation.environment
        if invocation.onlyPassedIndicators {
            // An empty data folder keeps MVT from loading every downloaded
            // indicator file; the picked ones are passed with --iocs.
            let empty = MVTEnvironment.emptyDataFolder
            try? FileManager.default.createDirectory(at: empty, withIntermediateDirectories: true)
            extraEnvironment["MVT_DATA_FOLDER"] = empty.path
            if !globalArgs.contains("--disable-indicator-update-check") {
                globalArgs.append("--disable-indicator-update-check")
            }
        }
        var commandArgs = invocation.arguments
        // Older releases only take --verbose after the command name, and only
        // on these commands.
        let takesVerbose: Set<String> = [
            "check-backup", "check-fs", "check-androidqf", "check-bugreport", "check-intrusion-logs",
        ]
        if environment.verbose && !environment.acceptsGlobalVerbose,
           let name = commandArgs.first, takesVerbose.contains(name) {
            commandArgs.insert("--verbose", at: 1)
        }
        let args = globalArgs + commandArgs
        // Show the script that actually runs (mvt-ios stands in for mvt on older releases).
        var display = ([executable.lastPathComponent] + args).map(Invocation.shellQuote).joined(separator: " ")
        if let dataFolder = extraEnvironment["MVT_DATA_FOLDER"] {
            display = "MVT_DATA_FOLDER=\(Invocation.shellQuote(dataFolder)) " + display
        }
        let secrets = invocation.environment.keys.sorted().map { "\($0)=•••• " }.joined()
        return await runner.run(
            executable: executable,
            arguments: args,
            environment: extraEnvironment,
            displayCommand: secrets + display
        )
    }

    @MainActor
    func showResults(at folder: String) {
        resultsFolder = folder
        selection = .results
    }
}
