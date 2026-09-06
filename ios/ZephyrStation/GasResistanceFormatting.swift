import Foundation

enum GasResistanceFormatting {
    static func display(kiloOhms: Double) -> String {
        if kiloOhms >= 1_000 {
            return String(format: "%.1f MΩ", kiloOhms / 1_000)
        }
        return String(format: "%.0f kΩ", kiloOhms)
    }

    static func spoken(kiloOhms: Double) -> String {
        if kiloOhms >= 1_000 {
            return String(format: "%.1f megaohms", kiloOhms / 1_000)
        }
        return String(format: "%.0f kilo-ohms", kiloOhms)
    }
}
