import Foundation

/// Fetches live weather data from the Zephyr API
class WeatherService {
    private let apiURL = URL(string: "https://yvsssrfmu6.execute-api.eu-central-1.amazonaws.com/v1/widget?device_id=mstation")!

    func fetchWeather() async throws -> WeatherResponse {
        let (data, _) = try await URLSession.shared.data(from: apiURL)
        return try JSONDecoder().decode(WeatherResponse.self, from: data)
    }

    func fetchHistory(metric: HistoryMetric, range: HistoryRange) async throws -> HistoryResponse {
        var components = URLComponents(string: "https://yvsssrfmu6.execute-api.eu-central-1.amazonaws.com/v1/history")!
        components.queryItems = [
            URLQueryItem(name: "device_id", value: "mstation"),
            URLQueryItem(name: "metric", value: metric.rawValue),
            URLQueryItem(name: "range", value: range.rawValue),
        ]

        let (data, _) = try await URLSession.shared.data(from: components.url!)

        let decoder = JSONDecoder()
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
        formatter.timeZone = TimeZone.current
        decoder.dateDecodingStrategy = .formatted(formatter)
        return try decoder.decode(HistoryResponse.self, from: data)
    }
}
