import { describe, it, expect, afterAll, beforeAll } from 'vitest';
import { buildApp } from '../../src/app.js';
import { getDb, closeDb } from '../../src/db.js';
import { hasPendingMigrations } from '../../src/db/migrate.js';

const API_KEY = 'test-key';
const DEVICE_ID = 'test-station';

const validPayload = {
  device_id: DEVICE_ID,
  timestamp: new Date().toISOString(),
  readings: {
    temperature_c: 22.5,
    humidity_pct: 65,
    pressure_hpa: 1013,
    pm25: 12,
    pm10: 18,
  },
  meta: {
    battery_v: 3.92,
    rssi: -65,
  },
};

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

describe('GET /ready', () => {
  it('reports ready with real PostgreSQL', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({ method: 'GET', url: '/ready' });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('ready');
    await app.close();
  });
});

describe('POST /v1/ingest', () => {
  it('accepts a valid reading with API key', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify(validPayload),
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('ok');
    expect(body.device_id).toBe(DEVICE_ID);
    await app.close();
  });

  it('accepts and returns the station gas-resistance range', async () => {
    const app = buildIntegrationApp();
    const payload = {
      ...validPayload,
      timestamp: new Date().toISOString(),
      readings: {
        ...validPayload.readings,
        gas_density: 6204,
      },
    };

    const ingest = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    expect(ingest.statusCode).toBe(200);

    const widget = await app.inject({
      method: 'GET',
      url: `/v1/widget?device_id=${DEVICE_ID}`,
    });
    expect(widget.statusCode).toBe(200);
    expect(JSON.parse(widget.body).readings.gas_density).toBe(6204);
    await app.close();
  });

  it('rejects gas resistance outside the station wire range', async () => {
    const app = buildIntegrationApp();
    const payload = {
      ...validPayload,
      readings: {
        ...validPayload.readings,
        gas_density: 65536,
      },
    };
    const res = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    expect(res.statusCode).toBe(400);
    expect(JSON.parse(res.body).error.message).toBe('Validation failed');
    await app.close();
  });

  it('rejects with 403 when API key is wrong', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': 'wrong-key', 'content-type': 'application/json' },
      body: JSON.stringify(validPayload),
    });
    expect(res.statusCode).toBe(403);
    await app.close();
  });

  it('rejects with 400 for malformed JSON', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: 'not-json',
    });
    expect(res.statusCode).toBe(400);
    expect(JSON.parse(res.body)).toEqual({ error: 'Invalid JSON body' });
    await app.close();
  });

  it('rejects with 400 for missing required fields', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify({ device_id: DEVICE_ID }),
    });
    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error.message).toBe('Validation failed');
    expect(Array.isArray(body.error.errors)).toBe(true);
    await app.close();
  });

  it('rejects with 400 for out-of-range values', async () => {
    const app = buildIntegrationApp();
    const payload = {
      ...validPayload,
      readings: {
        ...validPayload.readings,
        temperature_c: 100, // out of range (-50 to 60)
      },
    };
    const res = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    expect(res.statusCode).toBe(400);
    const body = JSON.parse(res.body);
    expect(body.error.message).toBe('Validation failed');
    await app.close();
  });

  it('is idempotent — same device_id + timestamp does not duplicate (COUNT=1)', async () => {
    const sql = getDb();
    const app = buildIntegrationApp();

    const payload = {
      ...validPayload,
      timestamp: '2026-08-30T12:00:00.000Z',
    };

    // First ingest
    const res1 = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    expect(res1.statusCode).toBe(200);

    // Second ingest with same data
    const res2 = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    expect(res2.statusCode).toBe(200);

    // Verify COUNT(*) = 1 for this exact (device_id, recorded_at)
    const countResult = await sql`SELECT COUNT(*)::int as count FROM readings WHERE device_id = ${DEVICE_ID} AND recorded_at = ${payload.timestamp}`;
    expect(countResult[0].count).toBe(1);

    await app.close();
  });
});

describe('GET /v1/widget', () => {
  it('returns the latest reading with correct station_status', async () => {
    const app = buildIntegrationApp();

    const payload = {
      ...validPayload,
      timestamp: new Date().toISOString(),
    };

    await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'x-api-key': API_KEY, 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const res = await app.inject({
      method: 'GET',
      url: `/v1/widget?device_id=${DEVICE_ID}`,
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.device_id).toBe(DEVICE_ID);
    expect(body.station_status).toBe('online');
    expect(body.data_age_seconds).toBeGreaterThanOrEqual(0);
    expect(body.data_age_seconds).toBeLessThan(10);
    await app.close();
  });

  it('returns 404 for unknown device', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'GET',
      url: '/v1/widget?device_id=nonexistent',
    });
    expect(res.statusCode).toBe(404);
    await app.close();
  });

  it('returns 400 for missing device_id', async () => {
    const app = buildIntegrationApp();
    const res = await app.inject({
      method: 'GET',
      url: '/v1/widget',
    });
    expect(res.statusCode).toBe(400);
    await app.close();
  });
});

afterAll(async () => {
  await closeDb();
});
