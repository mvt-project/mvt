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
                    Label("Indicators", systemImage: "shield.checkered")
                        .tag(SidebarItem.indicators)
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
                        Label {
                            Text(command.title)
                        } icon: {
                            Image(systemName: command.systemImage)
                                .foregroundStyle(Color.androidGreen)
                        }
                        .tag(SidebarItem.command(command))
                    }
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
            case .indicators:
                IndicatorsView()
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
                case .found(let version) where environment.isOutdated:
                    Image(systemName: "arrow.up.circle.fill").foregroundStyle(.orange)
                    Text("MVT \(version) · update available")
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

extension Color {
    /// Android's brand green (#3DDC84), used for the Android tools.
    static let androidGreen = Color(red: 61 / 255, green: 220 / 255, blue: 132 / 255)
}

extension MVTCommand {
    /// The accent for a command's screen: Android green for Android tools,
    /// the app's accent colour otherwise.
    var accent: Color { tool == .android ? .androidGreen : .accentColor }
}
