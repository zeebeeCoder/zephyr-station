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
        case .gas: "Gas resistance"
        case .battery: "Battery"
        }
    }

    var accessibilityName: String {
        switch self {
        case .temperature: "Temperature"
        case .humidity: "Humidity"
        case .pressure: "Pressure"
        case .pm25: "PM 2.5"
        case .pm10: "PM 10"
        case .pm1: "PM 1"
        case .windSpeed: "Wind speed"
        case .gas: "Gas and volatile organic compounds"
        case .battery: "Battery voltage"
        }
    }

    var iconName: String {
        switch self {
        case .temperature: "thermometer"
        case .humidity: "humidity"
        case .pressure: "gauge.medium"
        case .pm25: "aqi.medium"
        case .pm10: "aqi.low"
        case .pm1: "aqi.high"
        case .windSpeed: "wind"
        case .gas: "carbon.dioxide.cloud"
        case .battery: "battery.100"
        }
    }

    func format(_ value: Double, unit: String) -> String {
        if self == .gas {
            return GasResistanceFormatting.display(kiloOhms: value)
        }

        let decimals = switch self {
        case .humidity, .pressure, .pm1, .pm25, .pm10, .gas: 0
        case .temperature, .windSpeed: 1
        case .battery: 2
        }
        return "\(value.formatted(.number.precision(.fractionLength(decimals)))) \(unit)"
    }
}

enum HistoryRange: String, CaseIterable {
    case day = "24h"
    case week = "7d"
    case month = "30d"

    var displayName: String {
        switch self {
        case .day: "Last 24 hours"
        case .week: "Last 7 days"
        case .month: "Last 30 days"
        }
    }
}
