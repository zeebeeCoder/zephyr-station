import SwiftUI
import Charts

struct ContentView: View {
    @State private var selectedTab = 0
    @Environment(\.theme) private var theme

    var body: some View {
        TabView(selection: Binding(
            get: { selectedTab },
            set: { newValue in
                if newValue != selectedTab {
                    #if os(iOS)
                    UISelectionFeedbackGenerator().selectionChanged()
                    #endif
                }
                selectedTab = newValue
            }
        )) {
            LiveView()
                .tabItem { Label("Live", systemImage: "antenna.radiowaves.left.and.right") }
                .tag(0)
            ChartsView()
                .tabItem { Label("Charts", systemImage: "chart.xyaxis.line") }
                .tag(1)
            #if os(iOS)
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(2)
            #endif
        }
        .tint(theme.accent)
    }
}

// MARK: - Live View

struct LiveView: View {
    @State private var weather: WeatherResponse?
    @State private var errorMessage: String?
    @State private var selectedMetric: HistoryMetric?
    @Environment(\.theme) private var theme
    private let weatherService = WeatherService()

    var body: some View {
        NavigationStack {
            ZStack {
                if theme.background != .clear {
                    theme.background.ignoresSafeArea()
                }

                ScrollView {
                    VStack(spacing: 16) {
                        if let weather {
                            statusPill(weather: weather)

                            let columns = [
                                GridItem(.flexible(), spacing: 12),
                                GridItem(.flexible(), spacing: 12)
                            ]
                            LazyVGrid(columns: columns, spacing: 12) {
                                ReadingCard(label: "Temperature",
                                    value: String(format: "%.1f\u{00B0}C", weather.readings.temperatureC),
                                    icon: "thermometer",
                                    metric: .temperature, onTap: { selectedMetric = $0 })
                                ReadingCard(label: "Humidity",
                                    value: String(format: "%.0f%%", weather.readings.humidityPct),
                                    icon: "humidity",
                                    metric: .humidity, onTap: { selectedMetric = $0 })
                                ReadingCard(label: "Pressure",
                                    value: String(format: "%.0f hPa", weather.readings.pressureHpa),
                                    icon: "gauge.medium",
                                    metric: .pressure, onTap: { selectedMetric = $0 })
                                if let wind = weather.readings.windSpeedMs {
                                    ReadingCard(label: "Wind",
                                        value: String(format: "%.1f m/s", wind),
                                        icon: "wind",
                                        metric: .windSpeed, onTap: { selectedMetric = $0 })
                                }
                                if let pm25 = weather.readings.pm25 {
                                    ReadingCard(label: "PM2.5",
                                        value: "\(pm25) \u{00B5}g/m\u{00B3}",
                                        icon: "aqi.medium",
                                        metric: .pm25, onTap: { selectedMetric = $0 })
                                }
                                if let pm10 = weather.readings.pm10 {
                                    ReadingCard(label: "PM10",
                                        value: "\(pm10) \u{00B5}g/m\u{00B3}",
                                        icon: "aqi.low",
                                        metric: .pm10, onTap: { selectedMetric = $0 })
                                }
                                if let pm1 = weather.readings.pm1 {
                                    ReadingCard(label: "PM1",
                                        value: "\(pm1) \u{00B5}g/m\u{00B3}",
                                        icon: "aqi.high",
                                        metric: .pm1, onTap: { selectedMetric = $0 })
                                }
                                if let gas = weather.readings.gasDensity {
                                    ReadingCard(label: "Gas/VOC",
                                        value: String(format: "%.0f", gas),
                                        icon: "carbon.dioxide.cloud",
                                        metric: .gas, onTap: { selectedMetric = $0 })
                                }
                                ReadingCard(label: "Battery",
                                    value: String(format: "%.2fV", weather.meta.batteryV),
                                    icon: "battery.100",
                                    metric: .battery, onTap: { selectedMetric = $0 })
                                ReadingCard(label: "Signal",
                                    value: "\(weather.meta.rssi) dBm",
                                    icon: "antenna.radiowaves.left.and.right")
                            }
                        } else if let errorMessage {
                            Text(errorMessage)
                                .foregroundStyle(.red)
                                .font(.caption)
                        } else {
                            ProgressView("Loading...")
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Zephyr Station")
            .refreshable { await loadWeather() }
            .task { await loadWeather() }
            .sheet(item: $selectedMetric) { metric in
                MiniChartSheet(metric: metric)
                    .presentationDetents([.medium])
                    .presentationDragIndicator(.visible)
            }
        }
    }

    @ViewBuilder
    private func statusPill(weather: WeatherResponse) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(weather.stationStatus == "online" ? .green : .red)
                .frame(width: 8, height: 8)
            Text(weather.stationStatus.capitalized)
                .font(.system(.caption, design: theme.fontDesign))
                .foregroundStyle(theme.textSecondary)
            if let recordedDate = parseRecordedAt(weather.recordedAt) {
                Text("\u{2022}")
                    .foregroundStyle(theme.textSecondary)
                Text(recordedDate, style: .relative)
                    .font(.system(.caption, design: theme.fontDesign))
                    .foregroundStyle(theme.textSecondary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(
            Group {
                if theme.style == .glass {
                    Capsule().fill(.ultraThinMaterial)
                } else {
                    Capsule()
                        .fill(theme.cardBackground)
                        .overlay(Capsule().strokeBorder(theme.cardBorder.opacity(0.3), lineWidth: 1))
                }
            }
        )
    }

    private func parseRecordedAt(_ str: String) -> Date? {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
        f.timeZone = TimeZone.current
        return f.date(from: str)
    }

    private func loadWeather() async {
        do {
            weather = try await weatherService.fetchWeather()
            #if os(iOS)
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            #endif
        } catch {
            errorMessage = "Could not load weather data"
            #if os(iOS)
            UINotificationFeedbackGenerator().notificationOccurred(.error)
            #endif
        }
    }
}

// MARK: - Charts View

struct ChartsView: View {
    @Environment(\.theme) private var theme

    var body: some View {
        NavigationStack {
            ZStack {
                if theme.background != .clear {
                    theme.background.ignoresSafeArea()
                }
                ScrollView {
                    HistoryChartView()
                        .padding()
                }
            }
            .navigationTitle("History")
        }
    }
}

// MARK: - Settings View

#if os(iOS)
struct SettingsView: View {
    @EnvironmentObject private var themeManager: ThemeManager
    @StateObject private var activityManager = LiveActivityManager()
    @Environment(\.theme) private var theme

    var body: some View {
        NavigationStack {
            ZStack {
                if theme.background != .clear {
                    theme.background.ignoresSafeArea()
                }

                ScrollView {
                    VStack(spacing: 20) {
                        // Theme grid
                        VStack(alignment: .leading, spacing: 12) {
                            Text("THEME")
                                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                .foregroundStyle(.secondary)
                                .tracking(2)
                                .padding(.horizontal, 4)

                            LazyVGrid(columns: [
                                GridItem(.flexible(), spacing: 12),
                                GridItem(.flexible(), spacing: 12),
                                GridItem(.flexible(), spacing: 12)
                            ], spacing: 12) {
                                ForEach(AppTheme.allThemes) { t in
                                    themeCard(t)
                                }
                            }
                        }

                        // Dynamic Island
                        VStack(alignment: .leading, spacing: 12) {
                            Text("DYNAMIC ISLAND")
                                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                .foregroundStyle(.secondary)
                                .tracking(2)
                                .padding(.horizontal, 4)

                            HStack(spacing: 12) {
                                Image(systemName: activityManager.isActivityActive ? "record.circle.fill" : "record.circle")
                                    .font(.title2)
                                    .foregroundStyle(activityManager.isActivityActive ? theme.accent : .secondary)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text(activityManager.isActivityActive ? "Active" : "Off")
                                        .font(.system(.body, design: .monospaced, weight: .semibold))
                                    Text("Live temp on Dynamic Island")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }

                                Spacer()

                                Button(activityManager.isActivityActive ? "Stop" : "Start") {
                                    Task {
                                        if activityManager.isActivityActive {
                                            await activityManager.stopActivity()
                                        } else {
                                            await activityManager.startActivity()
                                        }
                                    }
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(activityManager.isActivityActive ? .red : theme.accent)
                            }
                            .padding(14)
                            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
                        }

                        // About
                        VStack(alignment: .leading, spacing: 12) {
                            Text("ABOUT")
                                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                .foregroundStyle(.secondary)
                                .tracking(2)
                                .padding(.horizontal, 4)

                            VStack(spacing: 0) {
                                aboutRow("Version", "1.0")
                                Divider().padding(.horizontal)
                                aboutRow("Station", "mstation")
                            }
                            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Settings")
        }
    }

    @ViewBuilder
    private func themeCard(_ t: AppTheme) -> some View {
        let isSelected = themeManager.current.id == t.id
        Button {
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
            withAnimation(.easeInOut(duration: 0.3)) {
                themeManager.select(t)
            }
        } label: {
            VStack(spacing: 8) {
                // Color swatch circle
                ZStack {
                    Circle()
                        .fill(t.background == .clear ? Color(.systemBackground) : t.background)
                        .frame(width: 50, height: 50)
                    Circle()
                        .strokeBorder(isSelected ? t.accent : (t.cardBorder == .clear ? Color(.separator) : t.cardBorder), lineWidth: isSelected ? 2.5 : 1)
                        .frame(width: 50, height: 50)
                    Image(systemName: t.icon)
                        .foregroundStyle(t.accent)
                        .font(.system(size: 20))
                }

                Text(t.name)
                    .font(.system(size: 12, weight: isSelected ? .bold : .medium, design: .monospaced))
                    .foregroundStyle(isSelected ? theme.accent : .secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .strokeBorder(isSelected ? theme.accent.opacity(0.5) : .clear, lineWidth: 1.5)
            )
        }
        .buttonStyle(.plain)
    }

    private func aboutRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(.primary)
            Spacer()
            Text(value)
                .font(.system(.body, design: .monospaced))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }

    private func themeDescription(_ id: String) -> String {
        switch id {
        case "system": return "Follows iPhone settings"
        case "light": return "Bright and clean"
        case "dark": return "Easy on the eyes"
        case "ocean": return "Deep sea blues"
        case "sunset": return "Warm amber glow"
        case "aurora": return "Northern lights green"
        default: return ""
        }
    }
}
#endif

// MARK: - Reading Card

struct ReadingCard: View {
    let label: String
    let value: String
    let icon: String
    var metric: HistoryMetric? = nil
    var onTap: ((HistoryMetric) -> Void)? = nil
    @Environment(\.theme) private var theme

    var body: some View {
        Button {
            if let metric, let onTap {
                #if os(iOS)
                UIImpactFeedbackGenerator(style: .medium).impactOccurred()
                #endif
                onTap(metric)
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundStyle(theme.accent)
                    .frame(width: 28)
                VStack(alignment: .leading, spacing: 1) {
                    Text(value)
                        .font(.system(.subheadline, design: theme.fontDesign, weight: .bold))
                        .foregroundStyle(theme.style == .ocean ? theme.textPrimary : .primary)
                        .minimumScaleFactor(0.7)
                        .lineLimit(1)
                    HStack(spacing: 4) {
                        Text(label)
                            .font(.caption2)
                            .foregroundStyle(theme.style == .ocean ? theme.textSecondary : .secondary)
                        if metric != nil {
                            Image(systemName: "chart.line.uptrend.xyaxis")
                                .font(.system(size: 8))
                                .foregroundStyle(theme.accent.opacity(0.5))
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(
                Group {
                    if theme.style == .glass {
                        RoundedRectangle(cornerRadius: 12).fill(.ultraThinMaterial)
                    } else {
                        RoundedRectangle(cornerRadius: 12)
                            .fill(theme.cardBackground)
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .strokeBorder(theme.cardBorder.opacity(0.3), lineWidth: 1)
                            )
                    }
                }
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Mini Chart Sheet

struct MiniChartSheet: View {
    let metric: HistoryMetric
    @State private var response: HistoryResponse?
    @State private var isLoading = true
    @State private var selectedDate: Date?
    @Environment(\.theme) private var theme

    private let service = WeatherService()

    private var selectedPoint: HistoryResponse.DataPoint? {
        guard let selectedDate, let points = response?.points, !points.isEmpty else { return nil }
        return points.min(by: {
            abs($0.t.timeIntervalSince(selectedDate)) < abs($1.t.timeIntervalSince(selectedDate))
        })
    }

    var body: some View {
        VStack(spacing: 16) {
            // Header
            Text(metric.displayName)
                .font(.system(.title2, design: .monospaced, weight: .bold))

            if isLoading {
                Spacer()
                ProgressView()
                Spacer()
            } else if let response, !response.points.isEmpty {
                // Tooltip
                if let point = selectedPoint {
                    HStack(spacing: 6) {
                        Text(formatTime(point.t))
                        Text("\u{2022}")
                        Text(String(format: "%.1f %@", point.v, response.unit))
                            .bold()
                    }
                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(.ultraThinMaterial, in: Capsule())
                } else {
                    Text("Last 24 hours")
                        .font(.system(size: 13, design: .monospaced))
                        .foregroundStyle(.secondary)
                }

                // Chart
                Chart(response.points) { point in
                    LineMark(
                        x: .value("Time", point.t),
                        y: .value(response.unit, point.v)
                    )
                    .foregroundStyle(theme.accent)
                    .interpolationMethod(.catmullRom)
                    .lineStyle(StrokeStyle(lineWidth: 2))

                    AreaMark(
                        x: .value("Time", point.t),
                        y: .value(response.unit, point.v)
                    )
                    .foregroundStyle(
                        .linearGradient(
                            colors: [theme.accent.opacity(0.2), theme.accent.opacity(0.02)],
                            startPoint: .top, endPoint: .bottom
                        )
                    )
                    .interpolationMethod(.catmullRom)

                    if let sel = selectedPoint, sel.t == point.t {
                        PointMark(
                            x: .value("Time", point.t),
                            y: .value(response.unit, point.v)
                        )
                        .foregroundStyle(theme.accent)
                        .symbolSize(50)

                        RuleMark(x: .value("Time", point.t))
                            .foregroundStyle(theme.accent.opacity(0.3))
                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                    }
                }
                .chartXSelection(value: $selectedDate)
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 5)) { value in
                        AxisGridLine()
                        AxisValueLabel {
                            if let date = value.as(Date.self) {
                                Text(formatTime(date))
                                    .font(.system(size: 9, design: .monospaced))
                            }
                        }
                    }
                }
                .chartYAxis {
                    AxisMarks { _ in
                        AxisGridLine()
                        AxisValueLabel()
                            .font(.system(size: 9, design: .monospaced))
                    }
                }

                // Stats
                let values = response.points.map(\.v)
                HStack {
                    miniStat("MIN", String(format: "%.1f", values.min() ?? 0), response.unit)
                    Spacer()
                    miniStat("AVG", String(format: "%.1f", values.reduce(0, +) / Double(values.count)), response.unit)
                    Spacer()
                    miniStat("MAX", String(format: "%.1f", values.max() ?? 0), response.unit)
                }
            } else {
                Spacer()
                Text("No data available")
                    .foregroundStyle(.secondary)
                Spacer()
            }
        }
        .padding()
        .task {
            do {
                response = try await service.fetchHistory(metric: metric, range: .day)
            } catch {}
            isLoading = false
        }
    }

    private func formatTime(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "HH:mm"
        return f.string(from: date)
    }

    private func miniStat(_ label: String, _ value: String, _ unit: String) -> some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundStyle(.secondary)
            Text("\(value) \(unit)")
                .font(.system(size: 13, weight: .bold, design: .monospaced))
        }
    }
}
