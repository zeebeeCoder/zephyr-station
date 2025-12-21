import { describe, it, expect } from 'vitest';
import {
  generateDiurnalTemperature,
  generateInverseHumidity,
  generateUrbanPM25,
  generatePM10,
  generatePressure,
  generateWindSpeed,
  generateWindDirection,
  generateBatteryVoltage,
  generateRSSI,
  generateReadings,
} from '@/lib/db/seed';

describe('Temperature Generator', () => {
  it('should generate coldest temperature around 4am', () => {
    const temps = Array.from({ length: 100 }, () => generateDiurnalTemperature(4));
    const avgTemp = temps.reduce((a, b) => a + b, 0) / temps.length;

    // At 4am, should be near minimum (around 5°C with base 12°C and amplitude 7)
    expect(avgTemp).toBeLessThan(8);
    expect(avgTemp).toBeGreaterThan(2);
  });

  it('should generate warmest temperature around 2pm (14:00)', () => {
    const temps = Array.from({ length: 100 }, () => generateDiurnalTemperature(14));
    const avgTemp = temps.reduce((a, b) => a + b, 0) / temps.length;

    // At 2pm, should be near maximum (around 19°C with base 12°C and amplitude 7)
    expect(avgTemp).toBeGreaterThan(16);
    expect(avgTemp).toBeLessThan(22);
  });

  it('should follow diurnal pattern (afternoon warmer than night)', () => {
    const morningTemps = Array.from({ length: 50 }, () => generateDiurnalTemperature(6));
    const afternoonTemps = Array.from({ length: 50 }, () => generateDiurnalTemperature(14));

    const avgMorning = morningTemps.reduce((a, b) => a + b, 0) / morningTemps.length;
    const avgAfternoon = afternoonTemps.reduce((a, b) => a + b, 0) / afternoonTemps.length;

    expect(avgAfternoon).toBeGreaterThan(avgMorning);
  });
});

describe('Humidity Generator', () => {
  it('should generate higher humidity for lower temperatures', () => {
    const coldHumidity = Array.from({ length: 50 }, () => generateInverseHumidity(5));
    const warmHumidity = Array.from({ length: 50 }, () => generateInverseHumidity(20));

    const avgCold = coldHumidity.reduce((a, b) => a + b, 0) / coldHumidity.length;
    const avgWarm = warmHumidity.reduce((a, b) => a + b, 0) / warmHumidity.length;

    expect(avgCold).toBeGreaterThan(avgWarm);
  });

  it('should keep humidity within valid range (30-95%)', () => {
    for (let temp = -10; temp <= 40; temp += 5) {
      const humidity = generateInverseHumidity(temp);
      expect(humidity).toBeGreaterThanOrEqual(30);
      expect(humidity).toBeLessThanOrEqual(95);
    }
  });
});

describe('PM2.5 Generator', () => {
  it('should generate higher PM2.5 during morning rush (7-9am)', () => {
    const rushHourPM = Array.from({ length: 100 }, () => generateUrbanPM25(8));
    const midnightPM = Array.from({ length: 100 }, () => generateUrbanPM25(2));

    const avgRush = rushHourPM.reduce((a, b) => a + b, 0) / rushHourPM.length;
    const avgMidnight = midnightPM.reduce((a, b) => a + b, 0) / midnightPM.length;

    expect(avgRush).toBeGreaterThan(avgMidnight);
  });

  it('should generate higher PM2.5 during evening rush (5-7pm)', () => {
    const rushHourPM = Array.from({ length: 100 }, () => generateUrbanPM25(18));
    const middayPM = Array.from({ length: 100 }, () => generateUrbanPM25(12));

    const avgRush = rushHourPM.reduce((a, b) => a + b, 0) / rushHourPM.length;
    const avgMidday = middayPM.reduce((a, b) => a + b, 0) / middayPM.length;

    expect(avgRush).toBeGreaterThan(avgMidday);
  });

  it('should generate PM10 > PM2.5', () => {
    for (let i = 0; i < 50; i++) {
      const pm25 = generateUrbanPM25(12);
      const pm10 = generatePM10(pm25);
      expect(pm10).toBeGreaterThanOrEqual(pm25);
    }
  });
});

describe('Other Generators', () => {
  it('should generate pressure within valid range', () => {
    let prev: number | undefined;
    for (let i = 0; i < 50; i++) {
      prev = generatePressure(prev);
      expect(prev).toBeGreaterThanOrEqual(990);
      expect(prev).toBeLessThanOrEqual(1040);
    }
  });

  it('should generate wind speed within valid range', () => {
    for (let i = 0; i < 50; i++) {
      const speed = generateWindSpeed();
      expect(speed).toBeGreaterThanOrEqual(0);
      expect(speed).toBeLessThanOrEqual(15);
    }
  });

  it('should generate wind direction within 0-359', () => {
    let prev: number | undefined;
    for (let i = 0; i < 50; i++) {
      prev = generateWindDirection(prev);
      expect(prev).toBeGreaterThanOrEqual(0);
      expect(prev).toBeLessThan(360);
    }
  });

  it('should generate battery voltage within valid range', () => {
    for (let hour = 0; hour < 24; hour++) {
      for (let day = 0; day < 7; day++) {
        const voltage = generateBatteryVoltage(hour, day);
        expect(voltage).toBeGreaterThanOrEqual(3.2);
        expect(voltage).toBeLessThanOrEqual(4.2);
      }
    }
  });

  it('should generate RSSI within typical range', () => {
    for (let i = 0; i < 50; i++) {
      const rssi = generateRSSI();
      expect(rssi).toBeGreaterThanOrEqual(-90);
      expect(rssi).toBeLessThanOrEqual(-30);
    }
  });
});

describe('Readings Generator', () => {
  it('should generate readings for specified number of days', () => {
    const readings = generateReadings({
      devices: [{ id: 'test-01', name: 'Test', location: 'Test' }],
      range: { days: 1 },
      interval: '5m',
      patterns: {
        temperature: 'diurnal',
        humidity: 'inverse-temp',
        pm25: 'urban',
        gaps: { probability: 0 }, // No gaps for predictable count
      },
    });

    // 1 day = 24 hours = 1440 minutes / 5 min interval = ~288 readings
    expect(readings.length).toBeGreaterThanOrEqual(280);
    expect(readings.length).toBeLessThanOrEqual(300);
  });

  it('should create gaps when configured', () => {
    const readingsNoGaps = generateReadings({
      devices: [{ id: 'test-01', name: 'Test', location: 'Test' }],
      range: { days: 1 },
      interval: '5m',
      patterns: {
        temperature: 'flat',
        humidity: 'flat',
        pm25: 'flat',
        gaps: { probability: 0 },
      },
    });

    const readingsWithGaps = generateReadings({
      devices: [{ id: 'test-01', name: 'Test', location: 'Test' }],
      range: { days: 1 },
      interval: '5m',
      patterns: {
        temperature: 'flat',
        humidity: 'flat',
        pm25: 'flat',
        gaps: { probability: 0.1 }, // 10% gap probability
      },
    });

    // With 10% gaps, we should have fewer readings
    expect(readingsWithGaps.length).toBeLessThan(readingsNoGaps.length);
  });

  it('should include all required fields in readings', () => {
    const readings = generateReadings({
      devices: [{ id: 'test-01', name: 'Test', location: 'Test' }],
      range: { days: 1 },
      interval: '15m',
      patterns: {
        temperature: 'diurnal',
        humidity: 'inverse-temp',
        pm25: 'urban',
        gaps: { probability: 0 },
      },
    });

    const sample = readings[0];
    expect(sample).toHaveProperty('device_id');
    expect(sample).toHaveProperty('recorded_at');
    expect(sample).toHaveProperty('temperature_c');
    expect(sample).toHaveProperty('humidity_pct');
    expect(sample).toHaveProperty('pressure_hpa');
    expect(sample).toHaveProperty('pm25');
    expect(sample).toHaveProperty('pm10');
    expect(sample).toHaveProperty('wind_speed_ms');
    expect(sample).toHaveProperty('wind_dir_deg');
    expect(sample).toHaveProperty('battery_v');
    expect(sample).toHaveProperty('rssi');
  });
});
