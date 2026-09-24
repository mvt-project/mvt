import AppKit
import SwiftUI

/// One entry of alerts.json, as written by AlertStore.as_json() in
/// src/mvt/common/alerts.py.
struct ResultAlert: Identifiable {
    let id: Int
    let level: String
    let module: String
    let message: String
    let eventTime: String
    let eventJSON: String
    let indicatorJSON: String?

    var rank: Int {
        switch level {
        case "CRITICAL": return 4
        case "HIGH": return 3
        case "MEDIUM": return 2
        case "LOW": return 1
        default: return 0
        }
    }

    var logLevel: LogLevel {
        switch rank {
        case 4: return .criticalAlert
        case 3: return .highAlert
        case 2: return .mediumAlert
        case 1: return .lowAlert
        default: return .infoAlert
        }
    }
}

struct ResultFile: Identifiable {
    var id: String { url.path }
    let url: URL
    let size: Int
}

struct ResultsView: View {
    @EnvironmentObject private var appState: AppState

    @State private var alerts: [ResultAlert] = []
    @State private var files: [ResultFile] = []
    @State private var info: [String: Any] = [:]
    @State private var loadError: String?
    @State private var selection: ResultAlert.ID?
    @State private var sortOrder = [KeyPathComparator(\ResultAlert.rank, order: .reverse)]
    @State private var searchText = ""

    private var filteredAlerts: [ResultAlert] {
        let query = searchText.trimmingCharacters(in: .whitespaces)
        let base = query.isEmpty ? alerts : alerts.filter {
            $0.message.localizedCaseInsensitiveContains(query)
                || $0.module.localizedCaseInsensitiveContains(query)
                || $0.eventJSON.localizedCaseInsensitiveContains(query)
        }
        return base.sorted(using: sortOrder)
    }

    var body: some View {
        VStack(spacing: 0) {
            Form {
                Section {
                    PathField(
                        title: "Results folder",
                        path: $appState.resultsFolder,
                        mode: .folder,
                        placeholder: "Choose a folder produced by a check"
                    )
                    if let target = info["target_path"] as? String {
                        LabeledContent("Analyzed") {
                            Text(target).lineLimit(1).truncationMode(.middle).help(target)
                        }
                    }
                    if let version = info["mvt_version"] as? String, let date = info["date"] as? String {
                        LabeledContent("Run") {
                            Text("\(date) · MVT \(version)").lineLimit(1).truncationMode(.tail)
                        }
                    }
                }
            }
            .formStyle(.grouped)
            .frame(height: info.isEmpty ? 90 : 150)
            .scrollDisabled(true)

            if let loadError {
                ContentUnavailable(title: "Can't read results", message: loadError, systemImage: "exclamationmark.triangle")
            } else if appState.resultsFolder.isEmpty {
                ContentUnavailable(
                    title: "No results selected",
                    message: "Run a check with a results folder, or choose an existing one.",
                    systemImage: "list.bullet.rectangle"
                )
            } else {
                summary
                Divider()
                HSplitView {
                    alertTable
                        .frame(minWidth: 320)
                    detail
                        .frame(minWidth: 220, idealWidth: 300)
                }
            }
        }
        .navigationTitle("Results")
        .toolbar {
            ToolbarItemGroup {
                Button {
                    load()
                } label: {
                    Label("Reload", systemImage: "arrow.clockwise")
                }
                .disabled(appState.resultsFolder.isEmpty)
                Button {
                    NSWorkspace.shared.open(URL(fileURLWithPath: appState.resultsFolder))
                } label: {
                    Label("Open in Finder", systemImage: "folder")
                }
                .disabled(appState.resultsFolder.isEmpty)
            }
        }
        .onAppear(perform: load)
        .onChange(of: appState.resultsFolder) { _ in load() }
    }

    // MARK: - Pieces

    private var summary: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                let levels: [(String, LogLevel)] = [
                    ("CRITICAL", .criticalAlert), ("HIGH", .highAlert), ("MEDIUM", .mediumAlert),
                    ("LOW", .lowAlert), ("INFORMATIONAL", .infoAlert),
                ]
                ForEach(levels.indices, id: \.self) { index in
                    let entry = levels[index]
                    AlertCountBadge(
                        name: entry.1.alertName,
                        count: alerts.filter { $0.level == entry.0 }.count,
                        color: entry.1.color
                    )
                }
                Spacer()
                TextField("Filter alerts", text: $searchText)
                    .textFieldStyle(.roundedBorder)
                    .frame(maxWidth: 200)
                Menu("Files (\(files.count))") {
                    ForEach(files) { file in
                        Button("\(file.url.lastPathComponent) — \(ByteCountFormatter.string(fromByteCount: Int64(file.size), countStyle: .file))") {
                            NSWorkspace.shared.open(file.url)
                        }
                    }
                }
                .fixedSize()
                .disabled(files.isEmpty)
            }
            Text("The lack of severe alerts does not mean a device is clean. Public indicators miss recent and targeted attacks — seek expert help if you have serious concerns.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
    }

    private var alertTable: some View {
        Table(filteredAlerts, selection: $selection, sortOrder: $sortOrder) {
            TableColumn("Level", value: \.rank) { alert in
                Text(alert.logLevel.alertName)
                    .fontWeight(.semibold)
                    .foregroundStyle(alert.logLevel.color)
            }
            .width(min: 60, ideal: 70, max: 90)
            TableColumn("Module", value: \.module)
                .width(min: 80, ideal: 140)
            TableColumn("Time", value: \.eventTime)
                .width(min: 80, ideal: 160)
            TableColumn("Message", value: \.message) { alert in
                Text(alert.message).help(alert.message)
            }
        }
        .overlay {
            if alerts.isEmpty {
                Text("No alerts were recorded in this folder.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var detail: some View {
        ScrollView {
            if let alert = alerts.first(where: { $0.id == selection }) {
                VStack(alignment: .leading, spacing: 12) {
                    Text(alert.message)
                        .font(.headline)
                        .textSelection(.enabled)
                    LabeledContent("Module", value: alert.module)
                    if !alert.eventTime.isEmpty {
                        LabeledContent("Time", value: alert.eventTime)
                    }
                    if let indicator = alert.indicatorJSON {
                        Text("Matched indicator").font(.subheadline.bold())
                        codeBlock(indicator)
                    }
                    Text("Event").font(.subheadline.bold())
                    codeBlock(alert.eventJSON)
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                Text("Select an alert to see the record that triggered it.")
                    .foregroundStyle(.secondary)
                    .padding()
            }
        }
    }

    private func codeBlock(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 11, design: .monospaced))
            .textSelection(.enabled)
            .padding(8)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 6))
    }

    // MARK: - Loading

    private func load() {
        alerts = []
        files = []
        info = [:]
        loadError = nil
        selection = nil

        let folder = appState.resultsFolder
        guard !folder.isEmpty else { return }
        let url = URL(fileURLWithPath: folder, isDirectory: true)
        let fm = FileManager.default

        guard let contents = try? fm.contentsOfDirectory(
            at: url, includingPropertiesForKeys: [.fileSizeKey], options: [.skipsHiddenFiles]
        ) else {
            loadError = "The folder \(folder) could not be read."
            return
        }
        files = contents
            .filter { ["json", "csv", "log"].contains($0.pathExtension) }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
            .map { ResultFile(url: $0, size: (try? $0.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0) }

        if let data = try? Data(contentsOf: url.appendingPathComponent("info.json")),
           let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            info = object
        }

        let alertsURL = url.appendingPathComponent("alerts.json")
        guard fm.fileExists(atPath: alertsURL.path) else { return }
        do {
            let data = try Data(contentsOf: alertsURL)
            let raw = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] ?? []
            alerts = raw.enumerated().map { index, entry in
                ResultAlert(
                    id: index,
                    level: entry["level"] as? String ?? "INFORMATIONAL",
                    module: entry["module"] as? String ?? "",
                    message: entry["message"] as? String ?? "",
                    eventTime: entry["event_time"] as? String ?? "",
                    eventJSON: Self.pretty(entry["event"]),
                    indicatorJSON: entry["matched_indicator"].flatMap { $0 is NSNull ? nil : Self.pretty($0) }
                )
            }
        } catch {
            loadError = "alerts.json could not be parsed: \(error.localizedDescription)"
        }
    }

    private static func pretty(_ value: Any?) -> String {
        guard let value, !(value is NSNull) else { return "null" }
        if JSONSerialization.isValidJSONObject(value),
           let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]) {
            return String(decoding: data, as: UTF8.self)
        }
        return String(describing: value)
    }
}

/// Small stand-in for ContentUnavailableView, which needs macOS 14.
struct ContentUnavailable: View {
    let title: String
    let message: String
    let systemImage: String

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: systemImage)
                .font(.system(size: 36))
                .foregroundStyle(.secondary)
            Text(title).font(.title3.bold())
            Text(message)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
