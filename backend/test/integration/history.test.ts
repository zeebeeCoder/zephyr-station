import { describe, it, expect, afterAll, beforeAll } from 'vitest';
import { buildApp } from '../../src/app.js';
import { getDb, closeDb } from '../../src/db.js';
import { hasPendingMigrations } from '../../src/db/migrate.js';

const API_KEY = 'test-key';
const DEVICE_ID = 'history-test';

beforeAll(() => {
  if (!process.env.INGEST_API_KEY) {
    process.env.INGEST_API_KEY = API_KEY;
  }
});

function buildIntegrationApp() {
  const sql = getDb();
  return buildApp({
    config: {
      DATABASE_URL: process.env.DATABASE_URL!,
      INGEST_API_KEY: process.env.INGEST_API_KEY || API_KEY,
      PORT: 3000,
      HOST: '0.0.0.0',
      LOG_LEVEL: 'silent',
      NODE_ENV: 'test',
    },
    sql,
    hasPendingMigrations,
  });
}

function hoursAgo(hours: number): string {
  const d = new Date();
  d.setHours(d.getHours() - hours);
  return d.toISOString();
}

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

async function insertReading(sql: any, data: {
  device_id: string;
  recorded_at: string;
  temperature_c?: number;
  humidity_pct?: number;
  pressure_hpa?: number;
  gas_density?: number;
  pm1?: number;
  pm25?: number;
  pm10?: number;
  wind_speed_ms?: number;
  battery_v?: number;
  system_amps?: number;
  rssi?: number;
}) {
  await sql`
    INSERT INTO devices (id, name)
    VALUES (${data.device_id}, ${data.device_id})
    ON CONFLICT (id) DO NOTHING
  `;
  await sql`
    INSERT INTO readings (
      device_id, recorded_at,
      temperature_c, humidity_pct, pressure_hpa, gas_density,
      pm1, pm25, pm10, wind_speed_ms,
      battery_v, system_amps, rssi
    ) VALUES (
      ${data.device_id}, ${data.recorded_at},
      ${data.temperature_c ?? null}, ${data.humidity_pct ?? null},
      ${data.pressure_hpa ?? null}, ${data.gas_density ?? null},
      ${data.pm1 ?? null}, ${data.pm25 ?? null},
      ${data.pm10 ?? null}, ${data.wind_speed_ms ?? null},
      ${data.battery_v ?? null}, ${data.system_amps ?? null},
      ${data.rssi ?? null}
    )
    ON CONFLICT (device_id, recorded_at) DO NOTHING
  `;
}

describe('GET /v1/history', () => {
  it('returns 400 for missing device_id', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'GET',
      url: '/v1/history?metric=temperature_c&range=24h',
    });
    expect(res.statusCode).toBe(400);
    expect(JSON.parse(res.body)).toEqual({ error: 'Missing device_id' });
    await app.close();
  });

  it('returns 400 for invalid metric', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'GET',
      url: '/v1/history?device_id=test&metric=invalid&range=24h',
    });
    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error).toContain('Invalid metric');
    await app.close();
  });

  it('returns 400 for injection-shaped metric input', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'GET',
      url: '/v1/history?device_id=test&metric=temperature_c; DROP TABLE readings; --&range=24h',
    });
    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error).toContain('Invalid metric');
    await app.close();
  });

  it('returns 400 for invalid range', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'GET',
      url: '/v1/history?device_id=test&metric=temperature_c&range=invalid',
    });
    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error).toContain('Invalid range');
    await app.close();
  });

  it('returns 200 with empty points for no data', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'GET',
      url: `/v1/history?device_id=empty-device&metric=temperature_c&range=24h`,
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.device_id).toBe('empty-device');
    expect(body.metric).toBe('temperature_c');
    expect(body.range).toBe('24h');
    expect(body.unit).toBe('°C');
    expect(body.points).toEqual([]);
    await app.close();
  });

  it('returns 24h raw points in ascending order', async () => {
    const sql = getDb();
    const app = buildIntegrationApp();

    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: hoursAgo(3), temperature_c: 24.0 });
    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: hoursAgo(2), temperature_c: 22.0 });
    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: hoursAgo(1), temperature_c: 20.0 });

    const res = await app.inject({
      method: 'GET',
      url: `/v1/history?device_id=${DEVICE_ID}&metric=temperature_c&range=24h`,
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.points.length).toBe(3);
    expect(body.points[0].v).toBe(24.0);
    expect(body.points[1].v).toBe(22.0);
    expect(body.points[2].v).toBe(20.0);
    await app.close();
  });

  it('returns 7d hourly averages with correct aggregation', async () => {
    const sql = getDb();
    const app = buildIntegrationApp();

    const baseHour = new Date();
    baseHour.setMinutes(0, 0, 0);
    const hour3d = new Date(baseHour);
    hour3d.setDate(hour3d.getDate() - 3);

    const t1 = new Date(hour3d); t1.setMinutes(0);
    const t2 = new Date(hour3d); t2.setMinutes(15);
    const t3 = new Date(hour3d); t3.setMinutes(30);

    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: t1.toISOString(), temperature_c: 20.0 });
    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: t2.toISOString(), temperature_c: 22.0 });
    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: t3.toISOString(), temperature_c: 24.0 });

    const res = await app.inject({
      method: 'GET',
      url: `/v1/history?device_id=${DEVICE_ID}&metric=temperature_c&range=7d`,
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    const point = body.points.find((p: any) => p.t.startsWith(t1.toISOString().slice(0, 13)));
    expect(point).toBeDefined();
    expect(point.v).toBe(22.0); // average of 20, 22, 24
    await app.close();
  });

  it('includes 30d data', async () => {
    const sql = getDb();
    const app = buildIntegrationApp();

    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: daysAgo(15), temperature_c: 15.0 });

    const res = await app.inject({
      method: 'GET',
      url: `/v1/history?device_id=${DEVICE_ID}&metric=temperature_c&range=30d`,
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.points.length).toBeGreaterThanOrEqual(1);
    await app.close();
  });

  it('omits null-valued points', async () => {
    const sql = getDb();
    const app = buildIntegrationApp();

    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: hoursAgo(1), gas_density: 10.5 });
    await insertReading(sql, { device_id: DEVICE_ID, recorded_at: hoursAgo(2) });

    const res = await app.inject({
      method: 'GET',
      url: `/v1/history?device_id=${DEVICE_ID}&metric=gas_density&range=24h`,
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.points.length).toBe(1);
    expect(body.points[0].v).toBe(10.5);
    await app.close();
  });

  it('supports all metrics with correct units', async () => {
    const sql = getDb();
    const app = buildIntegrationApp();

    const allMetricsDevice = 'all-metrics-test';
    const now = new Date().toISOString();
    await insertReading(sql, {
      device_id: allMetricsDevice, recorded_at: now,
      temperature_c: 20, humidity_pct: 50, pressure_hpa: 1013,
      gas_density: 10.5, pm1: 5, pm25: 12, pm10: 18,
      wind_speed_ms: 3.5, battery_v: 3.92, rssi: -65,
    });

    const metrics = [
      { metric: 'temperature_c', unit: '°C', value: 20 },
      { metric: 'humidity_pct', unit: '%', value: 50 },
      { metric: 'pressure_hpa', unit: 'hPa', value: 1013 },
      { metric: 'gas_density', unit: 'kΩ', value: 10.5 },
      { metric: 'pm1', unit: 'µg/m³', value: 5 },
      { metric: 'pm25', unit: 'µg/m³', value: 12 },
      { metric: 'pm10', unit: 'µg/m³', value: 18 },
      { metric: 'wind_speed_ms', unit: 'm/s', value: 3.5 },
      { metric: 'battery_v', unit: 'V', value: 3.92 },
    ];

    for (const { metric, unit, value } of metrics) {
      const res = await app.inject({
        method: 'GET',
        url: `/v1/history?device_id=${allMetricsDevice}&metric=${metric}&range=24h`,
      });
      expect(res.statusCode).toBe(200);
      const body = JSON.parse(res.body);
      expect(body.metric).toBe(metric);
      expect(body.unit).toBe(unit);
      expect(body.points.length).toBe(1);
      expect(body.points[0].v).toBe(value);
    }
    await app.close();
  });
});

afterAll(async () => {
  await closeDb();
});
