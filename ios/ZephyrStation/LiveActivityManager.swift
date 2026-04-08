#if os(iOS)
import ActivityKit
import Foundation

/// Manages the Live Activity lifecycle: start, poll for updates, stop.
@MainActor
class LiveActivityManager: ObservableObject {
    @Published var isActivityActive = false

    private var activity: Activity<ZephyrWidgetAttributes>?
    private var pollingTask: Task<Void, Never>?
    private let weatherService = WeatherService()

    func startActivity() async {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else {
            print("Live Activities are not enabled in Settings")
            return
        }

        guard let weather = try? await weatherService.fetchWeather() else {
            print("Could not fetch weather — check your internet connection")
            return
        }

        let state = ZephyrWidgetAttributes.ContentState(
            temperatureC: weather.readings.temperatureC,
            humidityPct: weather.readings.humidityPct,
            pressureHpa: weather.readings.pressureHpa,
            windSpeedMs: weather.readings.windSpeedMs,
            pm25: weather.readings.pm25,
            stationStatus: weather.stationStatus,
            lastUpdated: Date()
        )

        do {
            let content = ActivityContent(
                state: state,
                staleDate: Date().addingTimeInterval(120)
            )
            activity = try Activity.request(
                attributes: ZephyrWidgetAttributes(),
                content: content
            )
            isActivityActive = true
            startPolling()
        } catch {
            print("Failed to start Live Activity: \(error)")
        }
    }

    func stopActivity() async {
        pollingTask?.cancel()
        pollingTask = nil

        if let activity {
            let finalState = activity.content.state
            await activity.end(
                ActivityContent(state: finalState, staleDate: nil),
                dismissalPolicy: .immediate
            )
        }
        activity = nil
        isActivityActive = false
    }

    private func startPolling() {
        pollingTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(45))
                guard !Task.isCancelled else { break }

                if let weather = try? await weatherService.fetchWeather() {
                    let state = ZephyrWidgetAttributes.ContentState(
                        temperatureC: weather.readings.temperatureC,
                        humidityPct: weather.readings.humidityPct,
                        pressureHpa: weather.readings.pressureHpa,
                        windSpeedMs: weather.readings.windSpeedMs,
                        pm25: weather.readings.pm25,
                        stationStatus: weather.stationStatus,
                        lastUpdated: Date()
                    )
                    let content = ActivityContent(
                        state: state,
                        staleDate: Date().addingTimeInterval(120)
                    )
                    await activity?.update(content)
                }
            }
        }
    }
}
#endif
