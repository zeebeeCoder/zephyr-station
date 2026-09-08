import SwiftUI
import Charts

struct HistoryChartView: View {
    @State private var range: HistoryRange = .day
    @Environment(\.theme) private var theme

    private let sections: [(title: String, metrics: [HistoryMetric])] = [
        ("WEATHER", [.temperature, .humidity, .pressure, .windSpeed]),
        ("AIR QUALITY", [.pm1, .pm25, .pm10, .gas]),
        ("STATION", [.battery]),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Picker("Range", selection: $range) {
                ForEach(HistoryRange.allCases, id: \.self) { item in
                    Text(item.rawValue).tag(item)
                }
            }
            .pickerStyle(.segmented)
            .accessibilityLabel("History range")

            ForEach(sections, id: \.title) { section in
                VStack(alignment: .leading, spacing: 10) {
                    Text(section.title)
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .tracking(2)
                        .padding(.horizontal, 4)

                    ForEach(section.metrics) { metric in
                        MetricHistoryCard(metric: metric, range: range)
                    }
                }
            }
        }
    }
}

private struct MetricHistoryCard: View {
    let metric: HistoryMetric
    let range: HistoryRange

    @State private var response: HistoryResponse?
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var showsDetail = false
    @Environment(\.theme) private var theme

    private let service = WeatherService()

    var body: some View {
        Button {
            guard response?.points.isEmpty == false else { return }
            showsDetail = true
        } label: {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 10) {
                    Image(systemName: metric.iconName)
                        .font(.title3)
                        .foregroundStyle(theme.accent)
                        .frame(width: 26)

                    VStack(alignment: .leading, spacing: 1) {
                        Text(metric.accessibilityName)
                            .font(.system(.subheadline, design: .monospaced, weight: .semibold))
                        if let response, let latest = response.points.last {
                            Text("Latest \(metric.format(latest.v, unit: response.unit))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Spacer()

                    if response?.points.isEmpty == false {
                        Image(systemName: "chevron.right")
                            .font(.caption.bold())
                            .foregroundStyle(.tertiary)
                    }
                }

                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 90)
                } else if let response, !response.points.isEmpty {
                    compactChart(response)
                    statsRow(response)
                } else {
                    HStack(spacing: 8) {
                        Image(systemName: errorMessage == nil ? "chart.line.downtrend.xyaxis" : "exclamationmark.triangle")
                        Text(errorMessage ?? "No data in this period")
                    }
                    .font(.caption)
                    .foregroundStyle(errorMessage == nil ? Color.secondary : Color.red)
                    .frame(maxWidth: .infinity, minHeight: 90)
                }
            }
            .padding(14)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
            .contentShape(RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
        .accessibilityHint("Opens a detailed interactive chart")
        .task(id: range.rawValue) {
            await loadData()
        }
        .sheet(isPresented: $showsDetail) {
            MetricDetailChart(metric: metric, range: range)
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
    }

    @ViewBuilder
    private func compactChart(_ response: HistoryResponse) -> some View {
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
                    colors: [theme.accent.opacity(0.18), theme.accent.opacity(0.01)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .interpolationMethod(.catmullRom)
        }
        .frame(height: 90)
        .chartXAxis(.hidden)
        .chartYAxis(.hidden)
        .accessibilityHidden(true)
    }

    private func statsRow(_ response: HistoryResponse) -> some View {
        let values = response.points.map(\.v)
        let average = values.reduce(0, +) / Double(values.count)

        return HStack {
            CompactStat("MIN", metric.format(values.min() ?? 0, unit: response.unit))
            Spacer()
            CompactStat("AVG", metric.format(average, unit: response.unit))
            Spacer()
            CompactStat("MAX", metric.format(values.max() ?? 0, unit: response.unit))
        }
    }

    @MainActor
    private func loadData() async {
        isLoading = true
        errorMessage = nil

        do {
            // Avoid spending nine requests on an intermediate range while the
            // user is still moving through the segmented control.
            try await Task.sleep(for: .milliseconds(350))
            let result = try await service.fetchHistory(metric: metric, range: range)
            guard !Task.isCancelled else { return }
            response = result
        } catch is CancellationError {
            return
        } catch {
            guard !Task.isCancelled else { return }
            response = nil
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}

private struct CompactStat: View {
    let label: String
    let value: String

    init(_ label: String, _ value: String) {
        self.label = label
        self.value = value
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 11, weight: .bold, design: .monospaced))
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
    }
}

private struct MetricDetailChart: View {
    let metric: HistoryMetric
    let range: HistoryRange

    @State private var response: HistoryResponse?
    @State private var selectedDate: Date?
    @State private var isLoading = true
    @State private var errorMessage: String?
    @Environment(\.theme) private var theme

    private let service = WeatherService()

    private var selectedPoint: HistoryResponse.DataPoint? {
        guard let selectedDate, let points = response?.points, !points.isEmpty else { return nil }
        return points.min {
            abs($0.t.timeIntervalSince(selectedDate)) < abs($1.t.timeIntervalSince(selectedDate))
        }
    }

    var body: some View {
        NavigationStack {
            Group {
                if isLoading {
                    ProgressView()
                } else if let response, !response.points.isEmpty {
                    chart(response)
                } else {
                    ContentUnavailableView(
                        "No history",
                        systemImage: "chart.line.downtrend.xyaxis",
                        description: Text(errorMessage ?? "No data is available for this period.")
                    )
                }
            }
            .padding()
            .navigationTitle(metric.accessibilityName)
        }
        .task { await loadData() }
    }

    @ViewBuilder
    private func chart(_ response: HistoryResponse) -> some View {
        VStack(spacing: 16) {
            if let point = selectedPoint {
                Text("\(point.t.formatted(date: .abbreviated, time: .shortened))  •  \(metric.format(point.v, unit: response.unit))")
                    .font(.system(.caption, design: .monospaced, weight: .semibold))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(.ultraThinMaterial, in: Capsule())
            } else {
                Text("Touch and drag to inspect")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Chart(response.points) { point in
                LineMark(
                    x: .value("Time", point.t),
                    y: .value(response.unit, point.v)
                )
                .foregroundStyle(theme.accent)
                .interpolationMethod(.catmullRom)
                .lineStyle(StrokeStyle(lineWidth: 2.5))

                AreaMark(
                    x: .value("Time", point.t),
                    y: .value(response.unit, point.v)
                )
                .foregroundStyle(
                    .linearGradient(
                        colors: [theme.accent.opacity(0.22), theme.accent.opacity(0.02)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .interpolationMethod(.catmullRom)

                if let selectedPoint, selectedPoint.t == point.t {
                    RuleMark(x: .value("Time", point.t))
                        .foregroundStyle(theme.accent.opacity(0.4))
                    PointMark(
                        x: .value("Time", point.t),
                        y: .value(response.unit, point.v)
                    )
                    .foregroundStyle(theme.accent)
                    .symbolSize(60)
                }
            }
            .chartXSelection(value: $selectedDate)
            .chartXAxis {
                AxisMarks(values: .automatic(desiredCount: 5)) { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let date = value.as(Date.self) {
                            Text(axisLabel(date))
                        }
                    }
                }
            }

            let values = response.points.map(\.v)
            HStack {
                CompactStat("MIN", metric.format(values.min() ?? 0, unit: response.unit))
                Spacer()
                CompactStat("AVG", metric.format(values.reduce(0, +) / Double(values.count), unit: response.unit))
                Spacer()
                CompactStat("MAX", metric.format(values.max() ?? 0, unit: response.unit))
            }
        }
    }

    private func axisLabel(_ date: Date) -> String {
        switch range {
        case .day: date.formatted(date: .omitted, time: .shortened)
        case .week: date.formatted(.dateTime.weekday(.abbreviated))
        case .month: date.formatted(.dateTime.day().month(.abbreviated))
        }
    }

    @MainActor
    private func loadData() async {
        do {
            response = try await service.fetchHistory(metric: metric, range: range)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
