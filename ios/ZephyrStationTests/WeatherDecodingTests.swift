import XCTest
@testable import ZephyrStation

private final class MockURLProtocol: URLProtocol {
    static var requestCount = 0
    static var responseData = Data()

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        Self.requestCount += 1
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: 200,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Self.responseData)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

final class WeatherDecodingTests: XCTestCase {
    func testLatestReadingDecodesFractionalUTCDate() throws {
        let json = """
        {
          "device_id": "mstation",
          "recorded_at": "2026-09-06T10:15:30.123Z",
          "readings": {
            "temperature_c": 18.4,
            "humidity_pct": 67,
            "pressure_hpa": 1012.5,
            "gas_density": null,
            "pm1": null,
            "pm25": 8,
            "pm10": 12,
            "wind_speed_ms": 1.7
          },
          "meta": {
            "battery_v": 3.91,
            "system_amps": null,
            "rssi": -66
          },
          "station_status": "online",
          "data_age_seconds": 4
        }
        """

        let response = try WeatherService.makeDecoder().decode(
            WeatherResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertEqual(response.deviceId, "mstation")
        XCTAssertEqual(response.readings.temperatureC, 18.4)
        XCTAssertEqual(response.recordedAt.timeIntervalSince1970, 1_788_689_730.123, accuracy: 0.001)
    }

    func testHistoryDecodesUTCDateWithoutFractionalSeconds() throws {
        let json = """
        {
          "device_id": "mstation",
          "metric": "temperature_c",
          "range": "24h",
          "unit": "°C",
          "points": [
            { "t": "2026-09-06T10:15:30Z", "v": 18.4 }
          ]
        }
        """

        let response = try WeatherService.makeDecoder().decode(
            HistoryResponse.self,
            from: Data(json.utf8)
        )

        XCTAssertEqual(response.points.count, 1)
        XCTAssertEqual(response.points[0].v, 18.4)
        XCTAssertEqual(response.points[0].t.timeIntervalSince1970, 1_788_689_730, accuracy: 0.001)
    }

    func testHistoryResponsesAreCachedAcrossServiceInstances() async throws {
        let json = """
        {
          "device_id": "cache-test-station",
          "metric": "temperature_c",
          "range": "24h",
          "unit": "°C",
          "points": [
            { "t": "2026-09-06T10:15:30Z", "v": 18.4 }
          ]
        }
        """
        MockURLProtocol.requestCount = 0
        MockURLProtocol.responseData = Data(json.utf8)

        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockURLProtocol.self]
        let session = URLSession(configuration: configuration)

        let firstService = WeatherService(deviceID: "cache-test-station", session: session)
        let secondService = WeatherService(deviceID: "cache-test-station", session: session)

        _ = try await firstService.fetchHistory(metric: .temperature, range: .day)
        _ = try await secondService.fetchHistory(metric: .temperature, range: .day)

        XCTAssertEqual(MockURLProtocol.requestCount, 1)
    }

    func testInvalidTimestampIsRejected() {
        let json = """
        {
          "device_id": "mstation",
          "metric": "temperature_c",
          "range": "24h",
          "unit": "°C",
          "points": [
            { "t": "not-a-date", "v": 18.4 }
          ]
        }
        """

        XCTAssertThrowsError(
            try WeatherService.makeDecoder().decode(
                HistoryResponse.self,
                from: Data(json.utf8)
            )
        )
    }
}
