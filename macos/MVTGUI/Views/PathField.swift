import AppKit
import SwiftUI
import UniformTypeIdentifiers

/// A labeled path chooser backed by NSOpenPanel/NSSavePanel that also
/// accepts files dragged from Finder.
struct PathField: View {
    enum Mode {
        case folder
        case file
        case fileOrFolder
        case saveFile(defaultName: String)
    }

    let title: String
    @Binding var path: String
    let mode: Mode
    var placeholder = "None"

    @State private var isTargeted = false

    var body: some View {
        LabeledContent(title) {
            HStack(spacing: 6) {
                Text(path.isEmpty ? placeholder : (path as NSString).abbreviatingWithTildeInPath)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .foregroundStyle(path.isEmpty ? Color.secondary : Color.primary)
                    .help(path)
                    .frame(maxWidth: .infinity, alignment: .leading)
                if !path.isEmpty {
                    Button {
                        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
                    } label: {
                        Image(systemName: "magnifyingglass")
                    }
                    .buttonStyle(.borderless)
                    .help("Reveal in Finder")
                    Button {
                        path = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                    }
                    .buttonStyle(.borderless)
                    .foregroundStyle(.secondary)
                    .help("Clear")
                }
                Button("Choose…", action: choose)
            }
            .padding(2)
            .background(
                RoundedRectangle(cornerRadius: 5)
                    .stroke(Color.accentColor, lineWidth: isTargeted ? 2 : 0)
            )
        }
        .onDrop(of: [UTType.fileURL], isTargeted: $isTargeted) { providers in
            guard let provider = providers.first else { return false }
            _ = provider.loadObject(ofClass: URL.self) { url, _ in
                guard let url else { return }
                DispatchQueue.main.async { path = url.path }
            }
            return true
        }
    }

    private func choose() {
        let startURL = path.isEmpty ? nil : URL(fileURLWithPath: path)

        if case .saveFile(let defaultName) = mode {
            let panel = NSSavePanel()
            panel.nameFieldStringValue = startURL?.lastPathComponent ?? defaultName
            panel.directoryURL = startURL?.deletingLastPathComponent()
            panel.canCreateDirectories = true
            if panel.runModal() == .OK, let url = panel.url { path = url.path }
            return
        }

        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canCreateDirectories = true
        switch mode {
        case .folder:
            panel.canChooseDirectories = true
            panel.canChooseFiles = false
        case .file:
            panel.canChooseDirectories = false
            panel.canChooseFiles = true
        case .fileOrFolder:
            panel.canChooseDirectories = true
            panel.canChooseFiles = true
        case .saveFile:
            break
        }
        if let startURL {
            panel.directoryURL = startURL.hasDirectoryPath ? startURL : startURL.deletingLastPathComponent()
        }
        panel.prompt = "Choose"
        if panel.runModal() == .OK, let url = panel.url { path = url.path }
    }
}

extension PathField.Mode {
    init(_ kind: InputKind) {
        switch kind {
        case .folder, .none: self = .folder
        case .file: self = .file
        case .fileOrFolder: self = .fileOrFolder
        }
    }
}
