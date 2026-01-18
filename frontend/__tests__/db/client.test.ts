import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { DuckDbClient, DuckDbAnalyticsClient } from '@/lib/db/client';

describe('DuckDbClient', () => {
  let client: DuckDbClient;
  const testDbPath = ':memory:';

  beforeAll(async () => {
    client = new DuckDbClient(testDbPath);

    // Initialize schema manually for in-memory db
    await client.query(`
      CREATE TABLE devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        installed_at TIMESTAMP,
        is_active BOOLEAN DEFAULT true
      )
    `);

    await client.query(`
      CREATE TABLE readings (
        id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL,
        recorded_at TIMESTAMP NOT NULL,
        temperature_c DECIMAL(4,1),
        humidity_pct DECIMAL(4,1),
        pressure_hpa DECIMAL(6,1),
        pm25 INTEGER,
        pm10 INTEGER,
        wind_speed_ms DECIMAL(4,1),
        wind_dir_deg INTEGER,
        battery_v DECIMAL(3,2),
        rssi INTEGER
      )
    `);
  });

  afterAll(async () => {
    await client.close();
  });

  it('should connect to DuckDB', async () => {
    const result = await client.query('SELECT 1 as num');
    expect(result).toHaveLength(1);
    expect(result[0].num).toBe(1);
  });

  it('should insert and query devices', async () => {
    await client.query(`
      INSERT INTO devices (id, name, location, is_active)
      VALUES ('station-01', 'Garden Station', 'Backyard', true)
    `);

    const devices = await client.query<{ id: string; name: string }>(
      'SELECT id, name FROM devices WHERE id = ?',
      ['station-01']
    );

    expect(devices).toHaveLength(1);
    expect(devices[0].id).toBe('station-01');
    expect(devices[0].name).toBe('Garden Station');
  });

  it('should insert and query readings', async () => {
    const now = new Date().toISOString();

    await client.query(`
      INSERT INTO readings (id, device_id, recorded_at, temperature_c, humidity_pct)
      VALUES (1, 'station-01', '${now}', 22.5, 65.0)
    `);

    const readings = await client.query<{
      id: number;
      temperature_c: number;
      humidity_pct: number;
    }>('SELECT id, temperature_c, humidity_pct FROM readings WHERE id = 1');

    expect(readings).toHaveLength(1);
    expect(readings[0].temperature_c).toBeCloseTo(22.5, 1);
    expect(readings[0].humidity_pct).toBeCloseTo(65.0, 1);
  });

  it('should query with time range filter', async () => {
    // Insert multiple readings
    const baseTime = new Date('2024-01-15T12:00:00Z');

    for (let i = 0; i < 5; i++) {
      const recordedAt = new Date(baseTime.getTime() + i * 3600000); // +1 hour each
      await client.query(`
        INSERT INTO readings (id, device_id, recorded_at, temperature_c)
        VALUES (${100 + i}, 'station-01', '${recordedAt.toISOString()}', ${20 + i})
      `);
    }

    // Query readings in a specific range
    const start = new Date('2024-01-15T13:00:00Z').toISOString();
    const end = new Date('2024-01-15T15:00:00Z').toISOString();

    const readings = await client.query<{ id: number; temperature_c: number }>(
      `SELECT id, temperature_c FROM readings
       WHERE recorded_at >= '${start}' AND recorded_at <= '${end}'
       ORDER BY recorded_at`
    );

    expect(readings.length).toBeGreaterThanOrEqual(2);
  });

  it('should return empty array for no results', async () => {
    const result = await client.query(
      'SELECT * FROM devices WHERE id = ?',
      ['non-existent']
    );
    expect(result).toEqual([]);
  });
});

describe('DuckDbAnalyticsClient', () => {
  let client: DuckDbAnalyticsClient;

  beforeEach(async () => {
    // Reset environment for each test
    delete process.env.DATABASE_URL;
  });

  afterAll(async () => {
    if (client) {
      await client.close();
    }
  });

  it('should load postgres extension without error', async () => {
    client = new DuckDbAnalyticsClient();
    // The postgres extension is loaded on first query
    const result = await client.query('SELECT 1 as num');
    expect(result).toHaveLength(1);
    expect(result[0].num).toBe(1);
  });

  it('should work without postgres when DATABASE_URL not set', async () => {
    client = new DuckDbAnalyticsClient();

    // Create local tables since we're not attached to postgres
    await client.query(`
      CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL
      )
    `);
    await client.query(`
      CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL,
        recorded_at TIMESTAMP NOT NULL,
        temperature_c DECIMAL(4,1)
      )
    `);

    // Insert test data
    await client.query(`
      INSERT INTO devices (id, name) VALUES ('test-device', 'Test Device')
    `);

    // Query should work against local tables (no transformation)
    const devices = await client.query<{ id: string; name: string }>(
      'SELECT id, name FROM devices'
    );
    expect(devices).toHaveLength(1);
    expect(devices[0].id).toBe('test-device');
  });

  describe('query transformation', () => {
    it('should transform FROM readings to pg.public.readings when postgres attached', () => {
      // Access the private method for testing via prototype
      const clientInstance = new DuckDbAnalyticsClient();
      const routeToPostgres = (clientInstance as unknown as { routeToPostgres: (sql: string) => string }).routeToPostgres.bind(clientInstance);

      const sql = 'SELECT * FROM readings WHERE recorded_at > ?';
      const transformed = routeToPostgres(sql);
      expect(transformed).toBe('SELECT * FROM pg.public.readings WHERE recorded_at > ?');
    });

    it('should transform FROM devices to pg.public.devices when postgres attached', () => {
      const clientInstance = new DuckDbAnalyticsClient();
      const routeToPostgres = (clientInstance as unknown as { routeToPostgres: (sql: string) => string }).routeToPostgres.bind(clientInstance);

      const sql = 'SELECT id FROM devices WHERE is_active = true';
      const transformed = routeToPostgres(sql);
      expect(transformed).toBe('SELECT id FROM pg.public.devices WHERE is_active = true');
    });

    it('should transform JOIN clauses', () => {
      const clientInstance = new DuckDbAnalyticsClient();
      const routeToPostgres = (clientInstance as unknown as { routeToPostgres: (sql: string) => string }).routeToPostgres.bind(clientInstance);

      const sql = 'SELECT * FROM readings JOIN devices ON readings.device_id = devices.id';
      const transformed = routeToPostgres(sql);
      expect(transformed).toBe('SELECT * FROM pg.public.readings JOIN pg.public.devices ON readings.device_id = devices.id');
    });

    it('should handle case-insensitive table names', () => {
      const clientInstance = new DuckDbAnalyticsClient();
      const routeToPostgres = (clientInstance as unknown as { routeToPostgres: (sql: string) => string }).routeToPostgres.bind(clientInstance);

      const sql = 'SELECT * FROM READINGS WHERE id = 1';
      const transformed = routeToPostgres(sql);
      expect(transformed).toBe('SELECT * FROM pg.public.readings WHERE id = 1');
    });
  });
});
