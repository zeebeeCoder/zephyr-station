import Foundation

struct HistoryResponse: Codable {
    let deviceId: String
    let metric: String
    let range: String
    let unit: String
    let points: [DataPoint]

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case metric, range, unit, points
    }

    struct DataPoint: Codable, Identifiable {
        let t: Date
        let v: Double

        var id: Date { t }
    }
}

enum HistoryMetric: String, CaseIterable, Identifiable {
    var id: String { rawValue }

    case temperature = "temperature_c"
    case humidity = "humidity_pct"
    case pressure = "pressure_hpa"
    case pm25 = "pm25"
    case pm10 = "pm10"
    case pm1 = "pm1"
    case windSpeed = "wind_speed_ms"
    case gas = "gas_density"
    case battery = "battery_v"

    var displayName: String {
        switch self {
        case .temperature: "Temp"
        case .humidity: "Humidity"
        case .pressure: "Pressure"
        case .pm25: "PM2.5"
        case .pm10: "PM10"
        case .pm1: "PM1"
        case .windSpeed: "Wind"
        case .gas: "Gas/VOC"
        case .battery: "Battery"
        }
    }

    /// Subset shown in the Charts tab pickers
    static var chartCases: [HistoryMetric] {
        [.temperature, .pm25, .windSpeed]
    }
}

enum HistoryRange: String, CaseIterable {
    case day = "24h"
    case week = "7d"
    case month = "30d"
}
