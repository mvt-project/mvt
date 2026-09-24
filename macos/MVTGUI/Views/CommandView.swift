import SwiftUI

struct CommandView: View {
    @ObservedObject var form: CommandForm
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var runner: ProcessRunner
    @EnvironmentObject private var environment: MVTEnvironment

    /// Exit status of the last run started from this view, to offer
    /// follow-up actions.
    @State private var finishedCode: Int32?

    private var command: MVTCommand { form.command }

    var body: some View {
        VSplitView {
            VStack(spacing: 0) {
                Form {
                    header
                    fields
                }
                .formStyle(.grouped)
                actionBar
            }
            .frame(minHeight: 260, idealHeight: 420)

            ConsoleView()
                .frame(minHeight: 160)
        }
        .navigationTitle(command.title)
        .navigationSubtitle(command.tool.rawValue)
    }

    // MARK: - Sections

    private var header: some View {
        Section {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: command.systemImage)
                    .font(.system(size: 28))
                    .foregroundStyle(command.accent)
                    .frame(width: 36)
                VStack(alignment: .leading, spacing: 4) {
                    Text(command.summary)
                        .fixedSize(horizontal: false, vertical: true)
                    Link("Documentation", destination: command.docsURL)
                        .font(.callout)
                }
            }
            .padding(.vertical, 4)
        }
    }

    @ViewBuilder
    private var fields: some View {
        let options = command.options

        if command.inputKind != .none {
            Section("Input") {
                PathField(
                    title: command.inputLabel,
                    path: $form.inputPath,
                    mode: PathField.Mode(command.inputKind),
                    placeholder: "Choose or drop here"
                )
                if command == .iosCheckBackup {
                    Text("Finder backups live in ~/Library/Application Support/MobileSync/Backup/<UDID>. Encrypted backups must be decrypted first.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }

        if options.contains(.iosPassword) || options.contains(.androidPassword)
            || options.contains(.keyFileOutput) || options.contains(.destination) {
            Section(options.contains(.destination) ? "Decryption" : "Backup password") {
                if options.contains(.iosPassword) {
                    if command == .iosDecryptBackup {
                        Picker("Decrypt using", selection: $form.useKeyFile) {
                            Text("Password").tag(false)
                            Text("Key file").tag(true)
                        }
                        .pickerStyle(.segmented)
                    }
                    if form.useKeyFile && command == .iosDecryptBackup {
                        PathField(title: "Key file", path: $form.keyFilePath, mode: .file)
                    } else {
                        SecureField("Backup password", text: $form.password)
                    }
                }
                if options.contains(.androidPassword) {
                    SecureField("Backup password (if encrypted)", text: $form.password)
                }
                if options.contains(.keyFileOutput) {
                    PathField(
                        title: "Save key to",
                        path: $form.keyFileOutputPath,
                        mode: .saveFile(defaultName: "backup.key"),
                        placeholder: "Print to output"
                    )
                }
                if options.contains(.destination) {
                    PathField(title: "Destination folder", path: $form.destinationPath, mode: .folder)
                    Stepper("Parallel jobs: \(form.jobs)", value: $form.jobs, in: 1...32)
                }
                Text("Passwords are passed to MVT through an environment variable, never on the command line.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }

        if options.contains(.output) || options.contains(.iocs) {
            Section("Analysis") {
                if options.contains(.output) {
                    PathField(
                        title: "Results folder",
                        path: $form.outputPath,
                        mode: .folder,
                        placeholder: "Not saved (console only)"
                    )
                }
                if options.contains(.iocs) {
                    IndicatorChooser(form: form)
                }
                if options.contains(.module) {
                    LabeledContent("Module") {
                        HStack {
                            TextField("Module", text: $form.module, prompt: Text("All modules"))
                                .labelsHidden()
                            Button("List Modules") { Task { await listModules() } }
                                .disabled(runner.isRunning)
                        }
                    }
                }
                if options.contains(.timezone) {
                    TextField("Device timezone", text: $form.timezone, prompt: Text(timezonePrompt))
                }
                if options.contains(.fast) {
                    Toggle("Fast mode (skip time/resource consuming features)", isOn: $form.fast)
                }
                if options.contains(.hashes) {
                    Toggle("Generate hashes of all analyzed files", isOn: $form.hashes)
                }
            }
        }

        if options.contains(.virusTotal) {
            Section("VirusTotal") {
                Toggle("Look up APK hashes on VirusTotal", isOn: $form.virusTotal)
                if form.virusTotal {
                    SecureField("API key", text: $form.virusTotalAPIKey, prompt: Text("Uses MVT_VT_API_KEY if empty"))
                    Stepper("Delay between requests: \(form.virusTotalDelay)s", value: $form.virusTotalDelay, in: 0...120)
                }
                Text("Sends hashes of non-system packages to VirusTotal. Requires network access.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var timezonePrompt: String {
        command == .androidCheckBugreport ? "Read from the bug report" : "UTC"
    }

    private var actionBar: some View {
        let error = form.validationError()
        return HStack(spacing: 10) {
            if let error, !runner.isRunning {
                Label(error, systemImage: "info.circle")
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            } else if let finishedCode, !runner.isRunning {
                followUpActions(for: finishedCode)
            }
            Spacer()
            if runner.isRunning {
                Button("Stop", role: .destructive) { runner.cancel() }
            }
            Button {
                Task { await run() }
            } label: {
                Label(runButtonTitle, systemImage: "play.fill")
            }
            .keyboardShortcut(.return, modifiers: .command)
            .buttonStyle(.borderedProminent)
            .tint(command.accent)
            .disabled(error != nil || runner.isRunning || environment.binDirectory == nil)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(.bar)
    }

    private var runButtonTitle: String {
        switch command {
        case .iosDecryptBackup: return "Decrypt"
        case .iosExtractKey: return "Extract Key"
        default: return "Run Check"
        }
    }

    @ViewBuilder
    private func followUpActions(for code: Int32) -> some View {
        if code == 0 {
            if command.producesResults && !form.outputPath.isEmpty {
                Button("View Results") { appState.showResults(at: form.outputPath) }
            }
            if command == .iosDecryptBackup {
                Button("Check Decrypted Backup") {
                    let next = appState.form(for: .iosCheckBackup)
                    next.inputPath = form.destinationPath
                    appState.selection = .command(.iosCheckBackup)
                }
            }
        }
    }

    // MARK: - Actions

    @MainActor
    private func run() async {
        finishedCode = nil
        if command.producesResults && !form.outputPath.isEmpty {
            try? FileManager.default.createDirectory(
                atPath: form.outputPath, withIntermediateDirectories: true
            )
        }
        if command == .iosDecryptBackup {
            try? FileManager.default.createDirectory(
                atPath: form.destinationPath, withIntermediateDirectories: true
            )
        }
        let code = await appState.run(form.invocation(), title: command.title, environment: environment)
        finishedCode = code
    }

    @MainActor
    private func listModules() async {
        finishedCode = nil
        await appState.run(
            form.invocation(listModulesOnly: true),
            title: "\(command.title) — modules",
            environment: environment
        )
    }
}
