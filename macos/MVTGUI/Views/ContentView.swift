import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var environment: MVTEnvironment

    var body: some View {
        NavigationSplitView {
            List(selection: $appState.selection) {
                Section {
                    Label("Setup", systemImage: "wrench.and.screwdriver")
                        .tag(SidebarItem.setup)
                    Label("Results", systemImage: "list.bullet.rectangle")
                        .tag(SidebarItem.results)
                }
                Section("iOS") {
                    ForEach(MVTCommand.iosCommands) { command in
                        Label(command.title, systemImage: command.systemImage)
                            .tag(SidebarItem.command(command))
                    }
                }
                Section("Android") {
                    ForEach(MVTCommand.androidCommands) { command in
                        Label(command.title, systemImage: command.systemImage)
                            .tag(SidebarItem.command(command))
                    }
                }
                Section("Indicators") {
                    Label(MVTCommand.downloadIOCs.title, systemImage: MVTCommand.downloadIOCs.systemImage)
                        .tag(SidebarItem.command(.downloadIOCs))
                }
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 210, ideal: 230)
            .safeAreaInset(edge: .bottom) {
                MVTStatusFooter()
            }
        } detail: {
            switch appState.selection {
            case .setup, nil:
                SetupView()
            case .results:
                ResultsView()
            case .command(let command):
                CommandView(form: appState.form(for: command))
                    .id(command)
            }
        }
    }
}

private struct MVTStatusFooter: View {
    @EnvironmentObject private var environment: MVTEnvironment
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Button {
            appState.selection = .setup
        } label: {
            HStack(spacing: 6) {
                switch environment.status {
                case .found(let version):
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                    Text("MVT \(version)")
                case .missing:
                    Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
                    Text("MVT not installed")
                case .checking, .unknown:
                    ProgressView().controlSize(.small)
                    Text("Looking for MVT…")
                }
                Spacer()
            }
            .font(.caption)
            .lineLimit(1)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}
