import SwiftUI

@main
struct ZephyrStationApp: App {
    @StateObject private var themeManager = ThemeManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(themeManager)
                .environment(\.theme, themeManager.current)
                .preferredColorScheme(themeManager.current.colorScheme)
        }
    }
}
