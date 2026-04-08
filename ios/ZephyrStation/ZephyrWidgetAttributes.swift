#if os(iOS)
import ActivityKit
import Foundation

/// Shared between the main app and the widget extension.
/// Defines what data the Dynamic Island displays.
struct ZephyrWidgetAttributes: ActivityAttributes {
    /// Dynamic data that updates while the Live Activity is running
    struct ContentState: Codable, Hashable {
        var temperatureC: Double
        var humidityPct: Double
        var pressureHpa: Double
        var windSpeedMs: Double?
        var pm25: Int?
        var stationStatus: String
        var lastUpdated: Date
    }

    // No static attributes needed — all data is dynamic
}
#endif
