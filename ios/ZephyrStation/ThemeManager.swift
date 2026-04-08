import SwiftUI

// MARK: - Theme Style

enum ThemeStyle: String, Equatable {
    case glass
    case ocean
}

// MARK: - Theme Definition

struct AppTheme: Identifiable, Equatable {
    let id: String
    let name: String
    let icon: String
    let style: ThemeStyle
    let colorScheme: ColorScheme?
    let accent: Color
    let cardBackground: Color
    let cardBorder: Color
    let textPrimary: Color
    let textSecondary: Color
    let background: Color
    let fontDesign: Font.Design
}

extension AppTheme {
    static let system = AppTheme(
        id: "system", name: "System", icon: "circle.lefthalf.filled",
        style: .glass, colorScheme: nil,
        accent: .blue, cardBackground: .clear, cardBorder: .clear,
        textPrimary: .primary, textSecondary: .secondary,
        background: .clear, fontDesign: .monospaced
    )

    static let light = AppTheme(
        id: "light", name: "Light", icon: "sun.max.fill",
        style: .glass, colorScheme: .light,
        accent: .blue, cardBackground: .clear, cardBorder: .clear,
        textPrimary: .primary, textSecondary: .secondary,
        background: .clear, fontDesign: .monospaced
    )

    static let dark = AppTheme(
        id: "dark", name: "Dark", icon: "moon.fill",
        style: .glass, colorScheme: .dark,
        accent: .blue, cardBackground: .clear, cardBorder: .clear,
        textPrimary: .primary, textSecondary: .secondary,
        background: .clear, fontDesign: .monospaced
    )

    // Deep ocean — cool blues, dark navy
    static let ocean = AppTheme(
        id: "ocean", name: "Ocean", icon: "water.waves",
        style: .ocean, colorScheme: .dark,
        accent: Color(red: 0.3, green: 0.7, blue: 0.9),
        cardBackground: Color(red: 0.06, green: 0.12, blue: 0.2),
        cardBorder: Color(red: 0.15, green: 0.3, blue: 0.45),
        textPrimary: Color(red: 0.85, green: 0.92, blue: 0.97),
        textSecondary: Color(red: 0.4, green: 0.6, blue: 0.7),
        background: Color(red: 0.03, green: 0.08, blue: 0.14),
        fontDesign: .monospaced
    )

    // Sunset — warm amber/orange tones, deep purple-brown
    static let sunset = AppTheme(
        id: "sunset", name: "Sunset", icon: "sunset.fill",
        style: .ocean, colorScheme: .dark,
        accent: Color(red: 0.95, green: 0.55, blue: 0.25),
        cardBackground: Color(red: 0.15, green: 0.08, blue: 0.1),
        cardBorder: Color(red: 0.4, green: 0.2, blue: 0.15),
        textPrimary: Color(red: 0.97, green: 0.9, blue: 0.82),
        textSecondary: Color(red: 0.65, green: 0.45, blue: 0.35),
        background: Color(red: 0.08, green: 0.04, blue: 0.06),
        fontDesign: .monospaced
    )

    // Aurora — green/teal northern lights, dark base
    static let aurora = AppTheme(
        id: "aurora", name: "Aurora", icon: "sparkles",
        style: .ocean, colorScheme: .dark,
        accent: Color(red: 0.2, green: 0.85, blue: 0.6),
        cardBackground: Color(red: 0.05, green: 0.12, blue: 0.1),
        cardBorder: Color(red: 0.1, green: 0.35, blue: 0.25),
        textPrimary: Color(red: 0.85, green: 0.97, blue: 0.9),
        textSecondary: Color(red: 0.35, green: 0.6, blue: 0.5),
        background: Color(red: 0.02, green: 0.06, blue: 0.05),
        fontDesign: .monospaced
    )

    static let allThemes: [AppTheme] = [.system, .light, .dark, .ocean, .sunset, .aurora]
}

// MARK: - Theme Manager

@MainActor
class ThemeManager: ObservableObject {
    @AppStorage("selectedThemeId") private var selectedThemeId = "system"

    var current: AppTheme {
        AppTheme.allThemes.first { $0.id == selectedThemeId } ?? .system
    }

    func select(_ theme: AppTheme) {
        selectedThemeId = theme.id
        objectWillChange.send()
    }
}

// MARK: - Environment Key

struct ThemeKey: EnvironmentKey {
    static let defaultValue = AppTheme.system
}

extension EnvironmentValues {
    var theme: AppTheme {
        get { self[ThemeKey.self] }
        set { self[ThemeKey.self] = newValue }
    }
}
