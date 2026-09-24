import AppKit
import SwiftUI

/// Official sources of indicators and expert help, as listed in the MVT
/// README and docs (docs/iocs.md).
enum IndicatorLinks {
    static let officialList = URL(string: "https://github.com/mvt-project/mvt-indicators")!
    static let officialIndexFile = URL(string: "https://github.com/mvt-project/mvt-indicators/blob/main/indicators.yaml")!
    static let amnestyInvestigations = URL(string: "https://github.com/AmnestyTech/investigations")!
    static let stalkerware = URL(string: "https://github.com/AssoEchap/stalkerware-indicators")!
    static let docs = URL(string: "https://docs.mvt.re/en/latest/iocs/")!
    static let amnestyHelp = URL(string: "https://securitylab.amnesty.org/get-help/?c=mvt_docs")!
    static let accessNowHelpline = URL(string: "https://www.accessnow.org/help/")!
}

struct IndicatorsView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var environment: MVTEnvironment
    @EnvironmentObject private var runner: ProcessRunner
    @EnvironmentObject private var store: IndicatorStore

    var body: some View {
        VSplitView {
            Form {
                introSection
                officialSection
                downloadedSection
                sourcesSection
            }
            .formStyle(.grouped)
            .frame(minHeight: 300, idealHeight: 520)

            ConsoleView()
                .frame(minHeight: 120)
        }
        .navigationTitle("Indicators")
        .task {
            store.refreshDownloaded()
            if store.sets.isEmpty { await store.loadIndex() }
        }
        .alert(
            "Something went wrong",
            isPresented: Binding(get: { store.lastError != nil }, set: { if !$0 { store.lastError = nil } }),
            actions: { Button("OK") { store.lastError = nil } },
            message: { Text(store.lastError ?? "") }
        )
    }

    // MARK: - Sections

    private var introSection: some View {
        Section {
            VStack(alignment: .leading, spacing: 6) {
                bullet("Indicators are lists of known spyware traces (STIX2 files).")
                bullet("Every check compares the device data against the downloaded indicators.")
                bullet("Download them before your first check, and update them regularly.")
                bullet("Public indicators can't prove a device is clean. If you're worried, get expert help (links below).")
            }
            .padding(.vertical, 2)
        }
    }

    private var officialSection: some View {
        Section {
            HStack {
                Button {
                    Task { await downloadAll() }
                } label: {
                    Label("Download All", systemImage: "arrow.down.circle")
                }
                .buttonStyle(.borderedProminent)
                .disabled(runner.isRunning || !store.downloading.isEmpty || (environment.binDirectory == nil && store.sets.isEmpty))

                Button {
                    Task { await store.loadIndex() }
                } label: {
                    Label("Refresh List", systemImage: "arrow.clockwise")
                }
                .disabled(store.isLoadingIndex)

                Spacer()
                if store.isLoadingIndex {
                    ProgressView().controlSize(.small)
                } else if !store.sets.isEmpty {
                    let count = store.sets.filter { store.isDownloaded($0) }.count
                    Text("\(count) of \(store.sets.count) downloaded")
                        .foregroundStyle(.secondary)
                }
            }

            if let error = store.indexError {
                Label(error, systemImage: "wifi.exclamationmark")
                    .foregroundStyle(.orange)
            }

            ForEach(store.sets) { set in
                IndicatorSetRow(set: set)
            }
        } header: {
            Text("Official indicators")
        } footer: {
            Text("From MVT's official list (mvt-indicators) plus every other STIX2 file in the Amnesty International and Echap stalkerware repositories. “Download All” runs mvt download-iocs, then downloads the rest.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var downloadedSection: some View {
        Section {
            if store.downloaded.isEmpty {
                Text("No indicators downloaded yet.")
                    .foregroundStyle(.secondary)
            }
            ForEach(store.downloaded, id: \.self) { url in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(store.displayName(for: url))
                        Text(url.lastPathComponent)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                    Spacer()
                    Button {
                        NSWorkspace.shared.activateFileViewerSelecting([url])
                    } label: {
                        Image(systemName: "magnifyingglass")
                    }
                    .buttonStyle(.borderless)
                    .help("Show in Finder")
                    Button {
                        store.moveToTrash(url)
                    } label: {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.borderless)
                    .help("Move to Trash")
                }
            }
            HStack {
                Button("Import STIX2 File…", action: importFiles)
                Button("Open Folder") {
                    try? FileManager.default.createDirectory(at: IndicatorsIndex.folder, withIntermediateDirectories: true)
                    NSWorkspace.shared.open(IndicatorsIndex.folder)
                }
            }
        } header: {
            Text("Downloaded indicators")
        } footer: {
            Text("Stored in \((IndicatorsIndex.folder.path as NSString).abbreviatingWithTildeInPath). To use only some of them in a check, press “Choose Indicators…” in that check.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var sourcesSection: some View {
        Section("Where indicators come from") {
            Link("MVT's official indicator list (mvt-indicators)", destination: IndicatorLinks.officialList)
            Link("The index file MVT downloads from (indicators.yaml)", destination: IndicatorLinks.officialIndexFile)
            Link("Amnesty International investigations", destination: IndicatorLinks.amnestyInvestigations)
            Link("Stalkerware indicators", destination: IndicatorLinks.stalkerware)
            Link("MVT documentation on indicators", destination: IndicatorLinks.docs)
            Link("Get expert help: Amnesty International Security Lab", destination: IndicatorLinks.amnestyHelp)
            Link("Get expert help: Access Now Digital Security Helpline", destination: IndicatorLinks.accessNowHelpline)
        }
    }

    private func bullet(_ text: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Text("•")
            Text(text).fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Actions

    @MainActor
    private func downloadAll() async {
        if store.sets.isEmpty { await store.loadIndex() }
        // Prefer MVT's own command for the sets in its list: it also records
        // when indicators were last updated, which MVT's update check uses.
        // The app downloads the rest, and everything if the command fails.
        var remaining = store.sets
        if environment.binDirectory != nil {
            let form = appState.form(for: .downloadIOCs)
            let status = await appState.run(form.invocation(), title: "Download indicators", environment: environment)
            store.refreshDownloaded()
            if status == 0 { remaining = store.sets.filter { !$0.inMVTIndex } }
        }
        await store.download(remaining)
        if !remaining.isEmpty {
            runner.appendNote("Downloaded \(remaining.count) more indicator file\(remaining.count == 1 ? "" : "s") from the source repositories.")
        }
    }

    private func importFiles() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        panel.prompt = "Import"
        guard panel.runModal() == .OK else { return }
        for url in panel.urls { store.importFile(url) }
    }
}

private struct IndicatorSetRow: View {
    let set: IndicatorSet
    @EnvironmentObject private var store: IndicatorStore

    var body: some View {
        HStack(alignment: .top) {
            Image(systemName: store.isDownloaded(set) ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(store.isDownloaded(set) ? Color.green : Color.secondary)
            VStack(alignment: .leading, spacing: 2) {
                Text(set.name)
                if !set.sources.isEmpty {
                    Text(set.sources.joined(separator: ", ") + (set.inMVTIndex ? "" : " · not in MVT's list"))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            if let first = set.references.first {
                if set.references.count == 1 {
                    Link("Details", destination: first).font(.callout)
                } else {
                    Menu("Details") {
                        ForEach(set.references, id: \.self) { url in
                            Button(url.host() ?? url.absoluteString) { NSWorkspace.shared.open(url) }
                        }
                    }
                    .fixedSize()
                }
            }
            if store.downloading.contains(set.id) {
                ProgressView().controlSize(.small)
            } else {
                Button(store.isDownloaded(set) ? "Update" : "Download") {
                    Task { await store.download([set]) }
                }
            }
        }
    }
}
