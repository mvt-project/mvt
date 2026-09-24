import SwiftUI

@main
struct MVTGUIApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var environment = MVTEnvironment()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .environmentObject(appState.runner)
                .environmentObject(environment)
                .frame(minWidth: 980, minHeight: 660)
                .onAppear { environment.refresh() }
        }
        .commands {
            SidebarCommands()
        }

        Settings {
            SettingsView()
                .environmentObject(environment)
        }
    }
}
