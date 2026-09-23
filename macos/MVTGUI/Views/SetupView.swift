import AppKit
import SwiftUI

struct SetupView: View {
    @EnvironmentObject private var environment: MVTEnvironment
    @EnvironmentObject private var runner: ProcessRunner

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
                case .found(let version):
                    Image(systemName: "checkmark.seal.fill")
                        .font(.title2)
                        .foregroundStyle(.green)
                    VStack(alignment: .leading) {
                        Text("MVT \(version) is ready").font(.headline)
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
                Button(environment.binDirectory == nil ? "Install MVT" : "Reinstall MVT") {
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
            infoRow(
                "Indicators",
                "Download the public indicators before your first check so that known spyware traces can be detected.",
                link: URL(string: "https://docs.mvt.re/en/latest/iocs/")!
            )
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

    @MainActor
    private func install() async {
        runner.clear()
        runner.title = "Installing MVT"
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
        try? FileManager.default.createDirectory(
            at: venv.deletingLastPathComponent(), withIntermediateDirectories: true
        )

        var status = await runner.run(executable: python.url, arguments: ["-m", "venv", "--clear", venv.path])
        guard status == 0 else { return }

        let venvPython = venv.appendingPathComponent("bin/python3")
        status = await runner.run(executable: venvPython, arguments: ["-m", "pip", "install", "--upgrade", "pip"])
        guard status == 0 else { return }

        var installArgs = ["-m", "pip", "install", "--upgrade"]
        switch source {
        case .pypi:
            installArgs.append("mvt")
        case .local:
            if editable { installArgs.append("--editable") }
            installArgs.append(sourcePath)
        }
        status = await runner.run(executable: venvPython, arguments: installArgs)
        guard status == 0 else { return }

        runner.appendNote("MVT installed. Download the public indicators next (Indicators ▸ Download Indicators).")
        environment.refresh()
    }
}
