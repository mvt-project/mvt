import AppKit
import SwiftUI

/// The "Indicators" row of a check's form: a summary of what the check will
/// use and a button that opens the picker.
struct IndicatorChooser: View {
    @ObservedObject var form: CommandForm
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var store: IndicatorStore
    @State private var showingPicker = false

    var body: some View {
        LabeledContent("Indicators") {
            HStack {
                Text(summary)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .multilineTextAlignment(.trailing)
                Button("Choose Indicators…") { showingPicker = true }
            }
        }
        .sheet(isPresented: $showingPicker) {
            IndicatorPicker(form: form) { appState.selection = .indicators }
                .environmentObject(store)
        }
    }

    private var summary: String {
        let extra = form.iocFiles.count
        let extraText = extra == 0 ? "" : " + \(extra) extra file\(extra == 1 ? "" : "s")"
        switch form.indicatorMode {
        case .allDownloaded:
            let count = store.downloaded.count
            if count == 0 && extra == 0 { return "None downloaded yet" }
            return "All downloaded (\(count))" + extraText
        case .picked:
            let picked = form.pickedIndicators.count
            if picked == 0 && extra == 0 { return "None picked" }
            return "\(picked) picked" + extraText
        }
    }
}

/// Sheet for choosing which indicators a check uses.
struct IndicatorPicker: View {
    @ObservedObject var form: CommandForm
    var openIndicatorsScreen: () -> Void

    @EnvironmentObject private var store: IndicatorStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Choose indicators").font(.title2.bold())
            Text("Indicators are lists of known spyware traces. The check compares the device data against the ones you choose here.")
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            Picker("Use", selection: $form.indicatorMode) {
                Text("All downloaded indicators (recommended)").tag(IndicatorMode.allDownloaded)
                Text("Only the ones I pick").tag(IndicatorMode.picked)
            }
            .pickerStyle(.radioGroup)

            GroupBox("Downloaded indicators") {
                downloadedList
            }

            GroupBox("Extra STIX2 files") {
                extraFiles
            }

            if form.indicatorMode == .picked && form.pickedIndicators.isEmpty && form.iocFiles.isEmpty {
                Label("Nothing picked: only MVT's built-in checks will run.", systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.orange)
            }

            HStack {
                Button("Get More Indicators…") {
                    dismiss()
                    openIndicatorsScreen()
                }
                Spacer()
                Button("Done") { dismiss() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 560)
        .task {
            store.refreshDownloaded()
            // Drop picks whose files were deleted since.
            let present = Set(store.downloaded.map(\.path))
            form.pickedIndicators = form.pickedIndicators.intersection(present)
            if store.sets.isEmpty { await store.loadIndex() }
        }
    }

    @ViewBuilder
    private var downloadedList: some View {
        if store.downloaded.isEmpty {
            HStack {
                Text("None downloaded yet.")
                    .foregroundStyle(.secondary)
                Spacer()
            }
            .padding(4)
        } else {
            VStack(alignment: .leading, spacing: 6) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(store.downloaded, id: \.self) { url in
                            Toggle(isOn: pickBinding(url.path)) {
                                Text(store.displayName(for: url))
                                    .help(url.lastPathComponent)
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(4)
                }
                .frame(minHeight: 80, maxHeight: 220)
                .disabled(form.indicatorMode == .allDownloaded)

                if form.indicatorMode == .picked {
                    HStack {
                        Button("Select All") { form.pickedIndicators = Set(store.downloaded.map(\.path)) }
                        Button("Select None") { form.pickedIndicators = [] }
                    }
                    .controlSize(.small)
                }
            }
        }
    }

    private var extraFiles: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(form.iocFiles, id: \.self) { file in
                HStack {
                    Text((file as NSString).lastPathComponent)
                        .help(file)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    Spacer()
                    Button {
                        form.iocFiles.removeAll { $0 == file }
                    } label: {
                        Image(systemName: "minus.circle.fill")
                    }
                    .buttonStyle(.borderless)
                    .foregroundStyle(.secondary)
                    .help("Remove")
                }
            }
            HStack {
                Button("Add STIX2 File…", action: addFiles)
                Spacer()
                Text("Used in either mode.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(4)
    }

    private func pickBinding(_ path: String) -> Binding<Bool> {
        Binding(
            get: { form.pickedIndicators.contains(path) },
            set: { picked in
                if picked { form.pickedIndicators.insert(path) } else { form.pickedIndicators.remove(path) }
            }
        )
    }

    private func addFiles() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        guard panel.runModal() == .OK else { return }
        for url in panel.urls where !form.iocFiles.contains(url.path) {
            form.iocFiles.append(url.path)
        }
    }
}
