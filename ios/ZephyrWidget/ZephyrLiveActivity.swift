#if os(iOS)
import ActivityKit
import SwiftUI
import WidgetKit

struct ZephyrLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: ZephyrWidgetAttributes.self) { context in
            // ── Lock Screen / Notification Banner ──
            HStack {
                Image(systemName: "thermometer")
                    .font(.title2)
                    .foregroundStyle(.blue)

                VStack(alignment: .leading) {
                    Text("Zephyr Station")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(String(format: "%.1f\u{00B0}C", context.state.temperatureC))
                        .font(.title.bold())
                }

                Spacer()

                VStack(alignment: .trailing) {
                    Text(context.state.pm25.map { "\($0) \u{00B5}g/m\u{00B3}" } ?? "-- \u{00B5}g/m\u{00B3}")
                        .font(.title3)
                    Image(systemName: "aqi.medium")
                        .foregroundStyle(.cyan)
                }
            }
            .padding()
            .activityBackgroundTint(.black.opacity(0.8))
            .activitySystemActionForegroundColor(.white)

        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    VStack(alignment: .leading) {
                        Image(systemName: "thermometer")
                            .foregroundStyle(.blue)
                        Text(String(format: "%.1f\u{00B0}", context.state.temperatureC))
                            .font(.title2.bold())
                    }
                }

                DynamicIslandExpandedRegion(.trailing) {
                    VStack(alignment: .trailing) {
                        Image(systemName: "aqi.medium")
                            .foregroundStyle(.cyan)
                        Text(context.state.pm25.map { "\($0)" } ?? "--")
                            .font(.title2.bold())
                        Text("PM2.5")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                DynamicIslandExpandedRegion(.bottom) {
                    VStack(spacing: 6) {
                        HStack(spacing: 12) {
                            Label(
                                String(format: "%.0f hPa", context.state.pressureHpa),
                                systemImage: "gauge.medium"
                            )
                            .font(.caption2)
                            if let wind = context.state.windSpeedMs {
                                Label(
                                    String(format: "%.1f m/s", wind),
                                    systemImage: "wind"
                                )
                                .font(.caption2)
                            }
                            if let pm25 = context.state.pm25 {
                                Label(
                                    "\(pm25) \u{00B5}g/m\u{00B3}",
                                    systemImage: "aqi.medium"
                                )
                                .font(.caption2)
                            }
                        }
                        .foregroundStyle(.secondary)
                        HStack {
                            Circle()
                                .fill(context.state.stationStatus == "online" ? .green : .red)
                                .frame(width: 6, height: 6)
                            Text("Zephyr \(context.state.stationStatus)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(context.state.lastUpdated, style: .relative)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            } compactLeading: {
                Image(systemName: "thermometer")
                    .foregroundStyle(.blue)
            } compactTrailing: {
                Text(String(format: "%.0f\u{00B0}", context.state.temperatureC))
                    .font(.caption.bold())
            } minimal: {
                Text(String(format: "%.0f\u{00B0}", context.state.temperatureC))
                    .font(.caption2)
            }
        }
    }
}
#endif
