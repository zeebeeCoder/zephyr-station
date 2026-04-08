import AppIntents
import Foundation

/// Metric options exposed to Siri / Shortcuts
enum ZephyrMetric: String, AppEnum {
    case temperature, humidity, pressure, pm25, pm10, pm1, wind, gas, battery

    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Zephyr Metric"
    static var caseDisplayRepresentations: [ZephyrMetric: DisplayRepresentation] = [
        .temperature: "Temperature",
        .humidity:    "Humidity",
        .pressure:    "Pressure",
        .pm25:        "PM2.5",
        .pm10:        "PM10",
        .pm1:         "PM1",
        .wind:        "Wind Speed",
        .gas:         "Air Quality",
        .battery:     "Battery",
    ]

    func format(from r: WeatherResponse.Readings, meta: WeatherResponse.Meta) -> String {
        switch self {
        case .temperature: return String(format: "%.1f°C", r.temperatureC)
        case .humidity:    return String(format: "%.0f%%", r.humidityPct)
        case .pressure:    return String(format: "%.0f hPa", r.pressureHpa)
        case .pm25:        return r.pm25.map { "\($0) micrograms per cubic meter" } ?? "no data"
        case .pm10:        return r.pm10.map { "\($0) micrograms per cubic meter" } ?? "no data"
        case .pm1:         return r.pm1.map  { "\($0) micrograms per cubic meter" } ?? "no data"
        case .wind:        return r.windSpeedMs.map { String(format: "%.1f meters per second", $0) } ?? "no data"
        case .gas:         return r.gasDensity.map  { String(format: "%.0f kilo-ohms", $0) } ?? "no data"
        case .battery:     return String(format: "%.2f volts", meta.batteryV)
        }
    }

    var spokenName: String {
        switch self {
        case .temperature: return "temperature"
        case .humidity:    return "humidity"
        case .pressure:    return "pressure"
        case .pm25:        return "PM2.5"
        case .pm10:        return "PM10"
        case .pm1:         return "PM1"
        case .wind:        return "wind speed"
        case .gas:         return "air quality"
        case .battery:     return "battery"
        }
    }
}

/// Parameterized intent: "Hey Siri, get Zephyr <metric>"
struct GetZephyrReadingIntent: AppIntent {
    static var title: LocalizedStringResource = "Get Zephyr Reading"
    static var description = IntentDescription("Get the latest reading from your Zephyr weather station.")

    @Parameter(title: "Metric")
    var metric: ZephyrMetric

    static var parameterSummary: some ParameterSummary {
        Summary("Get Zephyr \(\.$metric)")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let weather = try await WeatherService().fetchWeather()
        let value = metric.format(from: weather.readings, meta: weather.meta)
        return .result(dialog: IntentDialog("Zephyr \(metric.spokenName) is \(value)"))
    }
}

/// Pre-built shortcuts that show up automatically in Shortcuts/Siri
struct ZephyrShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: GetZephyrReadingIntent(),
            phrases: [
                "Get \(.applicationName) reading",
                "Check \(.applicationName)",
                "\(.applicationName) reading",
                "What's \(.applicationName) saying",
            ],
            shortTitle: "Atlas Reading",
            systemImageName: "thermometer.medium"
        )
    }
}
