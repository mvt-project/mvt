import AppKit
import SwiftUI

extension LogLevel {
    var color: Color {
        switch self {
        case .plain: return .primary
        case .command: return .secondary
        case .warning: return .orange
        case .error: return .red
        case .infoAlert: return .blue
        case .lowAlert: return Color(nsColor: .systemYellow)
        case .mediumAlert: return .orange
        case .highAlert, .criticalAlert: return .red
        }
    }

    var alertName: String {
        switch self {
        case .infoAlert: return "Info"
        case .lowAlert: return "Low"
        case .mediumAlert: return "Medium"
        case .highAlert: return "High"
        case .criticalAlert: return "Critical"
        default: return ""
        }
    }
}

/// Streams the output of the shared ProcessRunner.
struct ConsoleView: View {
    @EnvironmentObject private var runner: ProcessRunner
    @State private var alertsOnly = false
    @State private var autoScroll = true

    private var visibleLines: [LogLine] {
        alertsOnly
            ? runner.lines.filter { $0.level.isAlert || $0.level == .error || $0.level == .command }
            : runner.lines
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            output
        }
        .background(Color(nsColor: .textBackgroundColor))
    }

    private var header: some View {
        HStack(spacing: 10) {
            if runner.isRunning {
                ProgressView().controlSize(.small)
            } else if let code = runner.lastExitCode {
                Image(systemName: code == 0 ? "checkmark.circle.fill" : "xmark.octagon.fill")
                    .foregroundStyle(code == 0 ? Color.green : Color.red)
            }
            Text(runner.title.isEmpty ? "Output" : runner.title)
                .font(.headline)
                .lineLimit(1)

            ForEach(Array(LogLevel.allCases.filter(\.isAlert).reversed()), id: \.self) { level in
                if let count = runner.alertCounts[level], count > 0 {
                    AlertCountBadge(name: level.alertName, count: count, color: level.color)
                }
            }

            Spacer()

            Toggle("Alerts only", isOn: $alertsOnly)
                .toggleStyle(.checkbox)
            Toggle("Auto-scroll", isOn: $autoScroll)
                .toggleStyle(.checkbox)
            Button {
                let text = runner.lines.map(\.text).joined(separator: "\n")
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(text, forType: .string)
            } label: {
                Image(systemName: "doc.on.doc")
            }
            .help("Copy output")
            .disabled(runner.lines.isEmpty)
            Button {
                runner.clear()
                runner.title = ""
            } label: {
                Image(systemName: "trash")
            }
            .help("Clear output")
            .disabled(runner.isRunning || runner.lines.isEmpty)
        }
        .buttonStyle(.borderless)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.bar)
    }

    private var output: some View {
        ScrollViewReader { proxy in
            ScrollView([.vertical, .horizontal]) {
                LazyVStack(alignment: .leading, spacing: 1) {
                    ForEach(visibleLines) { line in
                        Text(line.text.isEmpty ? " " : line.text)
                            .font(.system(size: 11, design: .monospaced))
                            .fontWeight(line.level == .criticalAlert ? .bold : .regular)
                            .foregroundStyle(line.level.color)
                            .fixedSize(horizontal: true, vertical: false)
                            .id(line.id)
                    }
                }
                .textSelection(.enabled)
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .overlay {
                if runner.lines.isEmpty {
                    Text("Output from MVT will appear here.")
                        .foregroundStyle(.secondary)
                }
            }
            .onChange(of: runner.lines.last?.id) { _ in
                guard autoScroll, let last = visibleLines.last else { return }
                proxy.scrollTo(last.id, anchor: .bottomLeading)
            }
        }
    }
}

struct AlertCountBadge: View {
    let name: String
    let count: Int
    let color: Color

    var body: some View {
        Text("\(count) \(name)")
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.18), in: Capsule())
            .foregroundStyle(color)
    }
}
