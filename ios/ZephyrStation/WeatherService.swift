import Foundation

/// Fetches live weather data from the Zephyr API
class WeatherService {
    private let apiBaseURL = URL(string: "https://zephyr.home.dicr.tech/v1")!

    func fetchWeather() async throws -> WeatherResponse {
        let url = endpointURL(path: "widget", queryItems: [
            URLQueryItem(name: "device_id", value: "mstation"),
        ])
        let (data, _) = try await URLSession.shared.data(from: url)
        return try JSONDecoder().decode(WeatherResponse.self, from: data)
    }

    func fetchHistory(metric: HistoryMetric, range: HistoryRange) async throws -> HistoryResponse {
        let url = endpointURL(path: "history", queryItems: [
            URLQueryItem(name: "device_id", value: "mstation"),
            URLQueryItem(name: "metric", value: metric.rawValue),
            URLQueryItem(name: "range", value: range.rawValue),
        ])

        let (data, _) = try await URLSession.shared.data(from: url)

        let decoder = JSONDecoder()
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
        formatter.timeZone = TimeZone.current
        decoder.dateDecodingStrategy = .formatted(formatter)
        return try decoder.decode(HistoryResponse.self, from: data)
    }

    private func endpointURL(path: String, queryItems: [URLQueryItem]) -> URL {
        var components = URLComponents(
            url: apiBaseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false
        )!
        components.queryItems = queryItems
        return components.url!
    }
}
