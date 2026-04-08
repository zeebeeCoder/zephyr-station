import SwiftUI
import Charts

struct HistoryChartView: View {
    @State private var metric: HistoryMetric = .temperature
    @State private var range: HistoryRange = .day
    @State private var response: HistoryResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?
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
        VStack(spacing: 12) {
            // Metric picker
            Picker("Metric", selection: $metric) {
                ForEach(HistoryMetric.chartCases, id: \.self) { m in
                    Text(m.displayName).tag(m)
                }
            }
            .pickerStyle(.segmented)

            // Range picker
            Picker("Range", selection: $range) {
                ForEach(HistoryRange.allCases, id: \.self) { r in
                    Text(r.rawValue).tag(r)
                }
            }
            .pickerStyle(.segmented)

            // Chart area
            if isLoading {
                ProgressView()
                    .frame(height: 240)
            } else if let response, !response.points.isEmpty {
                chartContent(response: response)
            } else if let errorMessage {
                Text(errorMessage)
                    .foregroundStyle(.red)
                    .font(.caption)
                    .frame(height: 240)
            } else {
                Text("No data")
                    .foregroundStyle(.secondary)
                    .frame(height: 240)
            }
        }
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
        .onChange(of: metric) { _, _ in
            selectedDate = nil
            loadData()
        }
        .onChange(of: range) { _, _ in
            selectedDate = nil
            loadData()
        }
        .task { loadData() }
    }

    // MARK: - Chart

    @ViewBuilder
    private func chartContent(response: HistoryResponse) -> some View {
        VStack(spacing: 8) {
            // Tooltip when a point is selected
            if let point = selectedPoint {
                HStack(spacing: 6) {
                    Text(formatTooltipDate(point.t))
                    Text("\u{2022}")
                    Text(String(format: "%.1f %@", point.v, response.unit))
                        .bold()
                }
                .font(.system(size: 12, weight: .medium, design: .monospaced))
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(.ultraThinMaterial, in: Capsule())
            } else {
                Text("Tap chart to inspect")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 5)
            }

            // The chart
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
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .interpolationMethod(.catmullRom)

                // Highlight selected point
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
            .frame(height: 200)
            .chartXSelection(value: $selectedDate)
            .chartXAxis {
                AxisMarks(values: .automatic(desiredCount: 5)) { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let date = value.as(Date.self) {
                            Text(formatAxisLabel(date))
                                .font(.system(size: 9, design: .monospaced))
                        }
                    }
                }
            }
            .chartYAxis {
                AxisMarks { value in
                    AxisGridLine()
                    AxisValueLabel()
                        .font(.system(size: 9, design: .monospaced))
                }
            }
            .animation(.easeInOut(duration: 0.15), value: selectedDate)

            // Stats row
            statsRow(from: response.points, unit: response.unit)
        }
    }

    // MARK: - Helpers

    private func loadData() {
        Task {
            isLoading = true
            errorMessage = nil
            do {
                response = try await service.fetchHistory(metric: metric, range: range)
            } catch {
                errorMessage = "Could not load history"
            }
            isLoading = false
        }
    }

    private func formatTooltipDate(_ date: Date) -> String {
        let f = DateFormatter()
        switch range {
        case .day:   f.dateFormat = "HH:mm"
        case .week:  f.dateFormat = "EEE HH:mm"
        case .month: f.dateFormat = "d MMM HH:mm"
        }
        return f.string(from: date)
    }

    private func formatAxisLabel(_ date: Date) -> String {
        let f = DateFormatter()
        switch range {
        case .day:   f.dateFormat = "HH:mm"
        case .week:  f.dateFormat = "EEE"
        case .month: f.dateFormat = "d MMM"
        }
        return f.string(from: date)
    }

    private func statsRow(from points: [HistoryResponse.DataPoint], unit: String) -> some View {
        let values = points.map(\.v)
        let mn = values.min() ?? 0
        let mx = values.max() ?? 0
        let avg = values.reduce(0, +) / Double(values.count)

        return HStack {
            StatLabel("MIN", String(format: "%.1f", mn), unit)
            Spacer()
            StatLabel("AVG", String(format: "%.1f", avg), unit)
            Spacer()
            StatLabel("MAX", String(format: "%.1f", mx), unit)
        }
        .font(.system(size: 11, design: .monospaced))
    }
}

struct StatLabel: View {
    let label: String
    let value: String
    let unit: String

    init(_ label: String, _ value: String, _ unit: String) {
        self.label = label
        self.value = value
        self.unit = unit
    }

    var body: some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundStyle(.secondary)
            Text("\(value) \(unit)")
                .font(.system(size: 13, weight: .bold, design: .monospaced))
        }
    }
}
