import SwiftUI
import WidgetKit

// MARK: - Retro Color Palette (Amica / vintage instrument panel)

let retroCream    = Color(red: 0.96, green: 0.93, blue: 0.85)
let retroAmber    = Color(red: 0.93, green: 0.69, blue: 0.13)
let retroOrange   = Color(red: 0.87, green: 0.45, blue: 0.15)
let retroRed      = Color(red: 0.75, green: 0.22, blue: 0.17)
let retroGreen    = Color(red: 0.40, green: 0.65, blue: 0.32)
let retroDark     = Color(red: 0.12, green: 0.11, blue: 0.10)
let retroBrown    = Color(red: 0.35, green: 0.28, blue: 0.22)
let retroMuted    = Color(red: 0.65, green: 0.60, blue: 0.52)

// MARK: - Timeline Provider

struct ZephyrTimelineProvider: TimelineProvider {
    private let weatherService = WeatherService()

    func placeholder(in context: Context) -> ZephyrEntry {
        ZephyrEntry(date: Date(), temperatureC: 20.0, humidityPct: 50, pressureHpa: 1013, pm25: 12, windSpeedMs: 1.2, stationStatus: "online")
    }

    func getSnapshot(in context: Context, completion: @escaping (ZephyrEntry) -> Void) {
        completion(placeholder(in: context))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<ZephyrEntry>) -> Void) {
        Task {
            let entry: ZephyrEntry
            if let weather = try? await weatherService.fetchWeather() {
                entry = ZephyrEntry(
                    date: Date(),
                    temperatureC: weather.readings.temperatureC,
                    humidityPct: weather.readings.humidityPct,
                    pressureHpa: weather.readings.pressureHpa,
                    pm25: weather.readings.pm25,
                    windSpeedMs: weather.readings.windSpeedMs,
                    stationStatus: weather.stationStatus
                )
            } else {
                entry = placeholder(in: context)
            }
            let nextUpdate = Date().addingTimeInterval(5 * 60)
            let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
            completion(timeline)
        }
    }
}

struct ZephyrEntry: TimelineEntry {
    let date: Date
    let temperatureC: Double
    let humidityPct: Double
    let pressureHpa: Double
    let pm25: Int?
    let windSpeedMs: Double?
    let stationStatus: String
}

// MARK: - Helpers

func pm25Icon(for value: Int) -> String {
    if value <= 12 { return "aqi.low" }
    if value <= 35 { return "aqi.medium" }
    return "aqi.high"
}

func pm25ColorRetro(for value: Int) -> Color {
    if value <= 12 { return retroGreen }
    if value <= 35 { return retroAmber }
    if value <= 55 { return retroOrange }
    return retroRed
}

func pm25QualityLabel(for value: Int) -> String {
    if value <= 12 { return "GOOD" }
    if value <= 35 { return "MOD" }
    if value <= 55 { return "POOR" }
    if value <= 150 { return "BAD" }
    return "HAZ"
}

// Keep the old one for lock screen (which can't use custom colors)
func pm25Color(for value: Int) -> Color {
    if value <= 12 { return .green }
    if value <= 35 { return .yellow }
    if value <= 55 { return .orange }
    return .red
}

// MARK: - Retro Gauge View (reusable)

struct RetroGauge: View {
    let label: String
    let value: String
    let small: Bool

    init(_ label: String, _ value: String, small: Bool = false) {
        self.label = label
        self.value = value
        self.small = small
    }

    var body: some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.system(size: small ? 8 : 9, weight: .medium, design: .monospaced))
                .foregroundColor(retroMuted)
                .tracking(2)
            Text(value)
                .font(.system(size: small ? 14 : 18, weight: .bold, design: .monospaced))
                .foregroundColor(retroCream)
        }
        .padding(.horizontal, small ? 6 : 10)
        .padding(.vertical, small ? 4 : 6)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(retroDark)
                .overlay(
                    RoundedRectangle(cornerRadius: 4)
                        .strokeBorder(retroBrown, lineWidth: 1)
                )
        )
    }
}

// MARK: - iOS Lock Screen Widgets

#if os(iOS)

struct ZephyrCircularWidget: Widget {
    let kind = "ZephyrCircular"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            ZStack {
                AccessoryWidgetBackground()
                VStack(spacing: -2) {
                    Text("TMP")
                        .font(.system(size: 8, weight: .medium, design: .monospaced))
                        .foregroundStyle(.secondary)
                    Text(String(format: "%.0f\u{00B0}", entry.temperatureC))
                        .font(.system(size: 24, weight: .heavy, design: .monospaced))
                }
            }
            .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Temperature")
        .description("Current Zephyr temperature")
        .supportedFamilies([.accessoryCircular])
    }
}

struct ZephyrPM25CircularWidget: Widget {
    let kind = "ZephyrPM25Circular"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            ZStack {
                AccessoryWidgetBackground()
                VStack(spacing: -2) {
                    Text("PM")
                        .font(.system(size: 8, weight: .medium, design: .monospaced))
                        .foregroundStyle(.secondary)
                    Text(entry.pm25.map { "\($0)" } ?? "--")
                        .font(.system(size: 24, weight: .heavy, design: .monospaced))
                }
            }
            .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Air Quality")
        .description("PM2.5 reading from Zephyr")
        .supportedFamilies([.accessoryCircular])
    }
}

struct ZephyrInlineWidget: Widget {
    let kind = "ZephyrInline"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            HStack(spacing: 4) {
                Text(String(format: "%.0f\u{00B0}C", entry.temperatureC))
                Text("\u{2022}")
                Text("PM:\(entry.pm25.map { "\($0)" } ?? "--")")
            }
            .font(.system(.body, design: .monospaced))
            .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Temp & Air Quality")
        .description("Temperature and PM2.5")
        .supportedFamilies([.accessoryInline])
    }
}

struct ZephyrRectangularWidget: Widget {
    let kind = "ZephyrRectangular"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text("\u{2022} ZEPHYR STATION")
                        .widgetAccentable()
                    Spacer()
                    Text(entry.stationStatus == "online" ? "LIVE" : "OFF")
                        .foregroundStyle(entry.stationStatus == "online" ? .green : .red)
                }
                .font(.system(size: 10, weight: .bold, design: .monospaced))

                HStack(spacing: 0) {
                    Text(String(format: "%.0f\u{00B0}C", entry.temperatureC))
                        .font(.system(size: 22, weight: .heavy, design: .monospaced))
                        .widgetAccentable()
                    Spacer()
                    if let pm25 = entry.pm25 {
                        VStack(alignment: .trailing, spacing: 0) {
                            Text("PM \(pm25)")
                                .font(.system(size: 16, weight: .heavy, design: .monospaced))
                            Text(pm25QualityLabel(for: pm25))
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundStyle(pm25Color(for: pm25))
                        }
                    }
                }

                HStack(spacing: 6) {
                    Text(String(format: "HUM:%.0f%%", entry.humidityPct))
                    Text("\u{2022}")
                    Text(String(format: "%.0fhPa", entry.pressureHpa))
                }
                .font(.system(size: 10, weight: .medium, design: .monospaced))
                .foregroundStyle(.secondary)
            }
            .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Weather & Air Quality")
        .description("Temperature, PM2.5, and humidity")
        .supportedFamilies([.accessoryRectangular])
    }
}

// MARK: - Combo: Temp + Humidity

struct ZephyrTempHumWidget: Widget {
    let kind = "ZephyrTempHum"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            HStack(spacing: 0) {
                HStack(spacing: 4) {
                    Image(systemName: "thermometer.medium")
                        .font(.system(size: 16))
                        .widgetAccentable()
                    VStack(alignment: .leading, spacing: 0) {
                        Text("TEMP")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        Text(String(format: "%.0f\u{00B0}C", entry.temperatureC))
                            .font(.system(size: 20, weight: .heavy, design: .monospaced))
                    }
                }
                Spacer()
                HStack(spacing: 4) {
                    VStack(alignment: .trailing, spacing: 0) {
                        Text("HUM")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        Text(String(format: "%.0f%%", entry.humidityPct))
                            .font(.system(size: 20, weight: .heavy, design: .monospaced))
                    }
                    Image(systemName: "humidity.fill")
                        .font(.system(size: 16))
                }
            }
            .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Temp + Humidity")
        .description("Temperature and humidity side by side")
        .supportedFamilies([.accessoryRectangular])
    }
}

// MARK: - Combo: Temp + PM2.5

struct ZephyrTempPMWidget: Widget {
    let kind = "ZephyrTempPM"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            HStack(spacing: 0) {
                HStack(spacing: 4) {
                    Image(systemName: "thermometer.medium")
                        .font(.system(size: 16))
                        .widgetAccentable()
                    VStack(alignment: .leading, spacing: 0) {
                        Text("TEMP")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        Text(String(format: "%.0f\u{00B0}C", entry.temperatureC))
                            .font(.system(size: 20, weight: .heavy, design: .monospaced))
                    }
                }
                Spacer()
                HStack(spacing: 4) {
                    VStack(alignment: .trailing, spacing: 0) {
                        Text("PM2.5")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        Text(entry.pm25.map { "\($0)" } ?? "--")
                            .font(.system(size: 20, weight: .heavy, design: .monospaced))
                        if let pm25 = entry.pm25 {
                            Text(pm25QualityLabel(for: pm25))
                                .font(.system(size: 8, weight: .bold, design: .monospaced))
                                .foregroundStyle(pm25Color(for: pm25))
                        }
                    }
                    Image(systemName: entry.pm25.map { pm25Icon(for: $0) } ?? "aqi.medium")
                        .font(.system(size: 16))
                }
            }
            .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Temp + PM2.5")
        .description("Temperature and air quality side by side")
        .supportedFamilies([.accessoryRectangular])
    }
}

// MARK: - Combo: Temp + Wind

struct ZephyrTempWindWidget: Widget {
    let kind = "ZephyrTempWind"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            HStack(spacing: 0) {
                HStack(spacing: 4) {
                    Image(systemName: "thermometer.medium")
                        .font(.system(size: 16))
                        .widgetAccentable()
                    VStack(alignment: .leading, spacing: 0) {
                        Text("TEMP")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        Text(String(format: "%.0f\u{00B0}C", entry.temperatureC))
                            .font(.system(size: 20, weight: .heavy, design: .monospaced))
                    }
                }
                Spacer()
                HStack(spacing: 4) {
                    VStack(alignment: .trailing, spacing: 0) {
                        Text("WIND")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        Text(entry.windSpeedMs.map { String(format: "%.1f", $0) } ?? "--")
                            .font(.system(size: 20, weight: .heavy, design: .monospaced))
                        Text("m/s")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    Image(systemName: "wind")
                        .font(.system(size: 16))
                }
            }
            .containerBackground(.clear, for: .widget)
        }
        .configurationDisplayName("Temp + Wind")
        .description("Temperature and wind speed side by side")
        .supportedFamilies([.accessoryRectangular])
    }
}

#endif

// MARK: - macOS Desktop Small Widget

struct ZephyrDesktopSmallWidget: Widget {
    let kind = "ZephyrDesktopSmall"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            VStack(spacing: 6) {
                // Vintage nameplate
                HStack {
                    Text("\u{2022} ZEPHYR \u{2022}")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .tracking(3)
                        .foregroundColor(retroAmber)
                    Spacer()
                    Circle()
                        .fill(entry.stationStatus == "online" ? retroGreen : retroRed)
                        .frame(width: 6, height: 6)
                        .shadow(color: entry.stationStatus == "online" ? retroGreen.opacity(0.8) : retroRed.opacity(0.8), radius: 4)
                }

                Spacer()

                // Main temperature display — like an old dial readout
                VStack(spacing: 0) {
                    Text(String(format: "%.1f\u{00B0}", entry.temperatureC))
                        .font(.system(size: 36, weight: .bold, design: .monospaced))
                        .foregroundColor(retroCream)
                        .minimumScaleFactor(0.6)
                        .lineLimit(1)
                    Text("CELSIUS")
                        .font(.system(size: 9, weight: .medium, design: .monospaced))
                        .tracking(3)
                        .foregroundColor(retroMuted)
                }

                Spacer()

                // Bottom gauges
                HStack(spacing: 6) {
                    RetroGauge("PM2.5", entry.pm25.map { "\($0)" } ?? "--", small: true)
                    RetroGauge("HUM", String(format: "%.0f%%", entry.humidityPct), small: true)
                    RetroGauge("hPa", String(format: "%.0f", entry.pressureHpa), small: true)
                }
            }
            .padding(12)
            .containerBackground(for: .widget) {
                ZStack {
                    retroDark
                    // Subtle texture — old bakelite feel
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(retroBrown.opacity(0.4), lineWidth: 3)
                        .padding(4)
                }
            }
        }
        .configurationDisplayName("Zephyr Station")
        .description("Vintage weather readout")
        .supportedFamilies([.systemSmall])
    }
}

// MARK: - macOS Desktop Medium Widget

struct ZephyrDesktopMediumWidget: Widget {
    let kind = "ZephyrDesktopMedium"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: ZephyrTimelineProvider()) { entry in
            HStack(spacing: 0) {
                // Left panel — temperature
                VStack(spacing: 4) {
                    Text("\u{2022} ZEPHYR \u{2022}")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .tracking(3)
                        .foregroundColor(retroAmber)

                    Spacer()

                    VStack(spacing: -2) {
                        Text(String(format: "%.1f\u{00B0}", entry.temperatureC))
                            .font(.system(size: 38, weight: .bold, design: .monospaced))
                            .foregroundColor(retroCream)
                            .minimumScaleFactor(0.6)
                            .lineLimit(1)
                        Text("CELSIUS")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .tracking(3)
                            .foregroundColor(retroMuted)
                    }

                    Spacer()

                    // Status indicator
                    HStack(spacing: 4) {
                        Circle()
                            .fill(entry.stationStatus == "online" ? retroGreen : retroRed)
                            .frame(width: 6, height: 6)
                            .shadow(color: entry.stationStatus == "online" ? retroGreen.opacity(0.8) : retroRed.opacity(0.8), radius: 3)
                        Text(entry.stationStatus == "online" ? "STATION ONLINE" : "STATION OFFLINE")
                            .font(.system(size: 8, weight: .medium, design: .monospaced))
                            .foregroundColor(retroMuted)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)

                // Divider — vintage brass strip
                Rectangle()
                    .fill(
                        LinearGradient(
                            colors: [retroBrown.opacity(0.3), retroAmber.opacity(0.5), retroBrown.opacity(0.3)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .frame(width: 2)
                    .padding(.vertical, 10)

                // Right panel — gauges
                VStack(alignment: .leading, spacing: 8) {
                    // PM2.5 — primary
                    if let pm25 = entry.pm25 {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("AIR QUALITY")
                                .font(.system(size: 8, weight: .medium, design: .monospaced))
                                .tracking(2)
                                .foregroundColor(retroMuted)
                            HStack(spacing: 8) {
                                Text("\(pm25)")
                                    .font(.system(size: 28, weight: .bold, design: .monospaced))
                                    .foregroundColor(retroCream)
                                VStack(alignment: .leading, spacing: 0) {
                                    Text("PM2.5")
                                        .font(.system(size: 9, weight: .medium, design: .monospaced))
                                        .foregroundColor(retroMuted)
                                    Text(pm25QualityLabel(for: pm25))
                                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                                        .foregroundColor(pm25ColorRetro(for: pm25))
                                }
                            }
                        }
                    }

                    // Secondary readings
                    HStack(spacing: 10) {
                        RetroGauge("HUM", String(format: "%.0f%%", entry.humidityPct), small: true)
                        RetroGauge("hPa", String(format: "%.0f", entry.pressureHpa), small: true)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
            }
            .padding(.horizontal, 12)
            .containerBackground(for: .widget) {
                ZStack {
                    retroDark
                    RoundedRectangle(cornerRadius: 2)
                        .strokeBorder(retroBrown.opacity(0.4), lineWidth: 3)
                        .padding(4)
                }
            }
        }
        .configurationDisplayName("Zephyr Station")
        .description("Full vintage weather readout")
        .supportedFamilies([.systemMedium])
    }
}
