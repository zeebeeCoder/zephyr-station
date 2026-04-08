import Foundation

/// Maps to the JSON response from the Zephyr API
struct WeatherResponse: Codable {
    let deviceId: String
    let recordedAt: String
    let readings: Readings
    let meta: Meta
    let stationStatus: String

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case recordedAt = "recorded_at"
        case readings, meta
        case stationStatus = "station_status"
    }

    struct Readings: Codable {
        let temperatureC: Double
        let humidityPct: Double
        let pressureHpa: Double
        let windSpeedMs: Double?
        let gasDensity: Double?
        let pm1: Int?
        let pm25: Int?
        let pm10: Int?

        enum CodingKeys: String, CodingKey {
            case temperatureC = "temperature_c"
            case humidityPct = "humidity_pct"
            case pressureHpa = "pressure_hpa"
            case windSpeedMs = "wind_speed_ms"
            case gasDensity = "gas_density"
            case pm1, pm25, pm10
        }
    }

    struct Meta: Codable {
        let batteryV: Double
        let systemAmps: Double?
        let rssi: Int

        enum CodingKeys: String, CodingKey {
            case batteryV = "battery_v"
            case systemAmps = "system_amps"
            case rssi
        }
    }
}
