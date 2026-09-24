import AppKit
import SwiftUI

struct SetupView: View {
    @EnvironmentObject private var environment: MVTEnvironment
    @EnvironmentObject private var runner: ProcessRunner
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var indicators: IndicatorStore

    private enum Source: String, CaseIterable, Identifiable {
        case pypi = "PyPI release"
        case local = "Local source folder"
        var id: String { rawValue }
    }

    @AppStorage("installSource") private var sourceRaw = Source.pypi.rawValue
    @AppStorage("installSourcePath") private var sourcePath = ""
    @AppStorage("installEditable") private var editable = true

    private var source: Source { Source(rawValue: sourceRaw) ?? .pypi }

    var body: some View {
        VSplitView {
            Form {
                statusSection
                installSection
                acquisitionSection
                aboutSection
            }
            .formStyle(.grouped)
            .frame(minHeight: 300, idealHeight: 480)

            ConsoleView()
                .frame(minHeight: 140)
        }
        .navigationTitle("Setup")
    }

    // MARK: - Sections

    private var statusSection: some View {
        Section("Mobile Verification Toolkit") {
            HStack(spacing: 10) {
                switch environment.status {
                case .found(let version) where environment.isOutdated:
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.title2)
                        .foregroundStyle(.orange)
                    VStack(alignment: .leading) {
                        Text("MVT \(version) is out of date").font(.headline)
                        Text("Version \(environment.latestVersion ?? "") is available. Updating brings the latest checks and fixes.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        if let dir = environment.binDirectory {
                            Text((dir.path as NSString).abbreviatingWithTildeInPath)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                        }
                    }
                case .found(let version):
                    Image(systemName: "checkmark.seal.fill")
                        .font(.title2)
                        .foregroundStyle(.green)
                    VStack(alignment: .leading) {
                        Text("MVT \(version) is ready").font(.headline)
                        if let latest = environment.latestVersion, latest == version {
                            Text("Up to date").font(.caption).foregroundStyle(.secondary)
                        }
                        if let dir = environment.binDirectory {
                            Text((dir.path as NSString).abbreviatingWithTildeInPath)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                        }
                    }
                case .missing:
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.title2)
                        .foregroundStyle(.orange)
                    VStack(alignment: .leading) {
                        Text("MVT was not found").font(.headline)
                        Text("Install it below, or point Settings at an existing installation (e.g. from pipx or uv).")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                case .checking, .unknown:
                    ProgressView().controlSize(.small)
                    Text("Looking for MVT…")
                }
                Spacer()
                if environment.isOutdated {
                    Button("Update MVT") {
                        Task { await install(forcePyPI: true) }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(runner.isRunning)
                }
                Button("Check Again") { environment.refresh() }
                    .disabled(environment.status == .checking)
            }
        }
    }

    private var installSection: some View {
        Section {
            Picker("Install from", selection: $sourceRaw) {
                ForEach(Source.allCases) { Text($0.rawValue).tag($0.rawValue) }
            }
            if source == .local {
                PathField(title: "MVT source folder", path: $sourcePath, mode: .folder,
                          placeholder: "Folder containing pyproject.toml")
                Toggle("Editable install (source changes apply without reinstalling)", isOn: $editable)
            }
            HStack {
                Text("Creates a private Python environment in ~/Library/Application Support/MVT GUI. Requires Python 3.10 or newer (e.g. brew install python).")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Button(installButtonTitle) {
                    Task { await install() }
                }
                .disabled(runner.isRunning || (source == .local && !isValidSource))
            }
        } header: {
            Text("Install")
        } footer: {
            Text("Alternatively, from Terminal: pipx install mvt — then press Check Again.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var acquisitionSection: some View {
        Section("Acquiring data") {
            infoRow(
                "iPhone / iPad",
                "Create an encrypted backup in Finder (select the device, tick “Encrypt local backup”), or use idevicebackup2 from libimobiledevice (brew install libimobiledevice).",
                link: URL(string: "https://docs.mvt.re/en/latest/ios/backup/itunes/")!
            )
            infoRow(
                "Android",
                "Collect data with AndroidQF, then analyze its output folder with Check AndroidQF.",
                link: URL(string: "https://github.com/mvt-project/androidqf")!
            )
            VStack(alignment: .leading, spacing: 2) {
                HStack {
                    Text("Indicators").font(.headline)
                    Spacer()
                    Button(indicators.downloaded.isEmpty ? "Get Indicators…" : "Manage Indicators…") {
                        appState.selection = .indicators
                    }
                }
                Text(indicators.downloaded.isEmpty
                     ? "Download the public indicators before your first check, so that known spyware traces can be found."
                     : "\(indicators.downloaded.count) indicator files downloaded. Update them regularly.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var aboutSection: some View {
        Section("About") {
            Text("MVT is a forensic research tool for technologists and investigators, developed by Amnesty International's Security Lab. It is licensed for the consensual analysis of devices; analyzing data from people who have not consented is not permitted. It is not a tool for end-user self-assessment — if you are concerned about your device, seek expert help.")
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
            HStack {
                Link("Documentation", destination: URL(string: "https://docs.mvt.re/")!)
                Link("License", destination: URL(string: "https://docs.mvt.re/en/latest/license/")!)
                Link("Get help (Amnesty Security Lab)", destination: URL(string: "https://securitylab.amnesty.org/get-help/")!)
            }
        }
    }

    private func infoRow(_ title: String, _ text: String, link: URL) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text(title).font(.headline)
                Spacer()
                Link("Learn more", destination: link).font(.caption)
            }
            Text(text)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Installation

    private var isValidSource: Bool {
        !sourcePath.isEmpty
            && FileManager.default.fileExists(atPath: (sourcePath as NSString).appendingPathComponent("pyproject.toml"))
    }

    private var installButtonTitle: String {
        if environment.binDirectory == nil { return "Install MVT" }
        if environment.isOutdated && source == .pypi { return "Update MVT" }
        return "Reinstall MVT"
    }

    /// Installs or updates MVT in the app's own environment. `forcePyPI`
    /// installs the latest release whatever the "Install from" choice.
    @MainActor
    private func install(forcePyPI: Bool = false) async {
        let updating = environment.binDirectory != nil && environment.isOutdated
        let wasUsingOtherInstall = environment.binDirectory != nil && !environment.usesManagedInstall
        runner.clear()
        runner.title = updating ? "Updating MVT" : "Installing MVT"
        runner.appendNote("Looking for Python 3.10+…")

        let python = await Task.detached { MVTEnvironment.findPython() }.value
        guard let python else {
            runner.appendNote(
                "No Python 3.10 or newer was found. Install one with Homebrew (brew install python) or from python.org, then try again.",
                level: .error
            )
            return
        }
        runner.appendNote("Using Python \(python.version) at \(python.url.path)")

        let venv = MVTEnvironment.managedVenv
        // Whatever happens from here on changes the installation.
        defer { environment.refresh() }
        try? FileManager.default.createDirectory(
            at: venv.deletingLastPathComponent(), withIntermediateDirectories: true
        )

        var status = await runner.run(executable: python.url, arguments: ["-m", "venv", "--clear", venv.path])
        guard status == 0 else { return }

        let venvPython = venv.appendingPathComponent("bin/python3")
        status = await runner.run(executable: venvPython, arguments: ["-m", "pip", "install", "--upgrade", "pip"])
        guard status == 0 else { return }

        var installArgs = ["-m", "pip", "install", "--upgrade"]
        switch forcePyPI ? .pypi : source {
        case .pypi:
            installArgs.append("mvt")
        case .local:
            if editable { installArgs.append("--editable") }
            installArgs.append(sourcePath)
        }
        status = await runner.run(executable: venvPython, arguments: installArgs)
        guard status == 0 else { return }

        if wasUsingOtherInstall && !environment.customBinDirectory.isEmpty {
            runner.appendNote(
                "Installed. Settings points the app at \(environment.customBinDirectory); clear it there to use this new version.",
                level: .warning
            )
        } else if wasUsingOtherInstall {
            runner.appendNote("MVT \(updating ? "updated" : "installed"). The app now uses this copy; the old one is left untouched.")
        } else {
            runner.appendNote("MVT \(updating ? "updated" : "installed"). Next, download the indicators from the Indicators screen.")
        }
    }
}
