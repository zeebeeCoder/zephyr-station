import Foundation

/// Errors returned by the private Zephyr API client.
enum ZephyrAPIError: LocalizedError {
    case invalidResponse
    case httpStatus(Int)
    case invalidTimestamp(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The weather server returned an invalid response."
        case .httpStatus(404):
            return "No readings are available for this station yet."
        case .httpStatus(let status):
            return "The weather server returned HTTP \(status)."
        case .invalidTimestamp(let value):
            return "The weather server returned an invalid timestamp: \(value)"
        }
    }
}

/// Fetches live weather data from the Zephyr API.
final class WeatherService {
    static let defaultBaseURL = URL(string: "https://omarchy.tail4e6e78.ts.net/v1")!
    static let defaultDeviceID = "mstation"

    private let apiBaseURL: URL
    private let deviceID: String
    private let session: URLSession

    init(
        apiBaseURL: URL = WeatherService.defaultBaseURL,
        deviceID: String = WeatherService.defaultDeviceID,
        session: URLSession = .shared
    ) {
        self.apiBaseURL = apiBaseURL
        self.deviceID = deviceID
        self.session = session
    }

    func fetchWeather() async throws -> WeatherResponse {
        let url = endpointURL(path: "widget", queryItems: [
            URLQueryItem(name: "device_id", value: deviceID),
        ])
        return try await fetch(WeatherResponse.self, from: url)
    }

    func fetchHistory(metric: HistoryMetric, range: HistoryRange) async throws -> HistoryResponse {
        let url = endpointURL(path: "history", queryItems: [
            URLQueryItem(name: "device_id", value: deviceID),
            URLQueryItem(name: "metric", value: metric.rawValue),
            URLQueryItem(name: "range", value: range.rawValue),
        ])
        return try await fetch(HistoryResponse.self, from: url)
    }

    private func fetch<T: Decodable>(_ type: T.Type, from url: URL) async throws -> T {
        let (data, response) = try await session.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ZephyrAPIError.invalidResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw ZephyrAPIError.httpStatus(httpResponse.statusCode)
        }
        return try Self.makeDecoder().decode(type, from: data)
    }

    /// Shared API decoder. The backend emits UTC ISO-8601 values, with or
    /// without fractional seconds depending on the PostgreSQL value.
    static func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let value = try container.decode(String.self)

            let fractional = ISO8601DateFormatter()
            fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = fractional.date(from: value) {
                return date
            }

            let wholeSeconds = ISO8601DateFormatter()
            wholeSeconds.formatOptions = [.withInternetDateTime]
            if let date = wholeSeconds.date(from: value) {
                return date
            }

            throw ZephyrAPIError.invalidTimestamp(value)
        }
        return decoder
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
