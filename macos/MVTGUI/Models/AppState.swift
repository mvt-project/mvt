import Foundation

enum SidebarItem: Hashable {
    case setup
    case results
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
        runner.clear()
        runner.title = title
        guard let executable = environment.executableURL(for: invocation.tool) else {
            runner.appendNote(
                "MVT was not found. Install it from the Setup screen or set its location in Settings.",
                level: .error
            )
            return -1
        }
        let args = environment.globalArguments + invocation.arguments
        let display = Invocation(
            tool: invocation.tool, arguments: args, environment: invocation.environment
        ).displayString
        return await runner.run(
            executable: executable,
            arguments: args,
            environment: invocation.environment,
            displayCommand: display
        )
    }

    @MainActor
    func showResults(at folder: String) {
        resultsFolder = folder
        selection = .results
    }
}
