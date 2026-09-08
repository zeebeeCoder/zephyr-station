import XCTest
@testable import ZephyrStation

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
