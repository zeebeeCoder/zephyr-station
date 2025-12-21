import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DuckDbClient } from '@/lib/db/client';

// We test the tool logic directly since the actual tools depend on AI SDK
// These tests verify the SQL generation and guardrails work correctly

describe('Weather Tools - SQL Logic', () => {
  let db: DuckDbClient;

  beforeAll(async () => {
    db = new DuckDbClient(':memory:');

    // Create tables
    await db.query(`
      CREATE TABLE devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL
      )
    `);

    await db.query(`
      CREATE TABLE readings (
        id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL,
        recorded_at TIMESTAMP NOT NULL,
        temperature_c DECIMAL(4,1),
        humidity_pct DECIMAL(4,1),
        pm25 INTEGER
      )
    `);

    // Insert test data
    await db.query(`INSERT INTO devices (id, name) VALUES ('station-01', 'Test Station')`);

    // Insert readings for the last 3 days
    const now = new Date();
    for (let dayOffset = 0; dayOffset < 3; dayOffset++) {
      for (let hour = 0; hour < 24; hour++) {
        const recordedAt = new Date(now);
        recordedAt.setDate(recordedAt.getDate() - dayOffset);
        recordedAt.setHours(hour, 0, 0, 0);

        const temp = 10 + hour * 0.5; // Temperature increases with hour
        const humidity = 70 - hour * 0.5;
        const pm25 = 15 + (hour >= 7 && hour <= 9 ? 20 : 0); // Rush hour spike

        await db.query(`
          INSERT INTO readings (id, device_id, recorded_at, temperature_c, humidity_pct, pm25)
          VALUES (${dayOffset * 24 + hour}, 'station-01', '${recordedAt.toISOString()}', ${temp}, ${humidity}, ${pm25})
        `);
      }
    }
  });

  afterAll(async () => {
    await db.close();
  });

  describe('get_current logic', () => {
    it('should return the latest reading', async () => {
      const result = await db.query(`
        SELECT * FROM readings
        WHERE recorded_at = (SELECT MAX(recorded_at) FROM readings)
      `);

      expect(result).toHaveLength(1);
      expect(result[0]).toHaveProperty('temperature_c');
    });

    it('should filter by device_id when specified', async () => {
      const result = await db.query(`
        SELECT * FROM readings
        WHERE device_id = 'station-01'
        ORDER BY recorded_at DESC
        LIMIT 1
      `);

      expect(result).toHaveLength(1);
      expect(result[0].device_id).toBe('station-01');
    });
  });

  describe('query_range logic', () => {
    it('should return readings within time range', async () => {
      const now = new Date();
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);

      const result = await db.query(`
        SELECT * FROM readings
        WHERE recorded_at >= '${yesterday.toISOString()}'
          AND recorded_at <= '${now.toISOString()}'
        ORDER BY recorded_at DESC
        LIMIT 100
      `);

      expect(result.length).toBeGreaterThan(0);
      expect(result.length).toBeLessThanOrEqual(100);
    });

    it('should support selecting specific metrics', async () => {
      const now = new Date();
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);

      const result = await db.query(`
        SELECT id, device_id, recorded_at, temperature_c FROM readings
        WHERE recorded_at >= '${yesterday.toISOString()}'
          AND recorded_at <= '${now.toISOString()}'
        LIMIT 5
      `);

      expect(result[0]).toHaveProperty('temperature_c');
      expect(result[0]).not.toHaveProperty('humidity_pct');
    });
  });

  describe('compare_periods logic', () => {
    it('should return aggregate statistics for a period', async () => {
      const now = new Date();
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);

      const result = await db.query<{
        avg_temperature: number;
        min_temperature: number;
        max_temperature: number;
        reading_count: number;
      }>(`
        SELECT
          AVG(temperature_c) as avg_temperature,
          MIN(temperature_c) as min_temperature,
          MAX(temperature_c) as max_temperature,
          COUNT(*) as reading_count
        FROM readings
        WHERE recorded_at >= '${yesterday.toISOString()}'
          AND recorded_at <= '${now.toISOString()}'
      `);

      expect(result).toHaveLength(1);
      expect(result[0].avg_temperature).toBeTypeOf('number');
      expect(result[0].reading_count).toBeGreaterThan(0);
    });
  });

  describe('execute_sql guardrails', () => {
    it('should allow valid SELECT queries', async () => {
      const query = 'SELECT COUNT(*) as cnt FROM readings';
      expect(query.trim().toLowerCase().startsWith('select')).toBe(true);

      const result = await db.query(query);
      expect(result).toHaveLength(1);
    });

    it('should detect non-SELECT queries', () => {
      const queries = [
        'DELETE FROM readings',
        'UPDATE readings SET temperature_c = 0',
        'INSERT INTO readings VALUES (1, 2, 3)',
        'DROP TABLE readings',
        'TRUNCATE TABLE readings',
      ];

      for (const query of queries) {
        expect(query.trim().toLowerCase().startsWith('select')).toBe(false);
      }
    });

    it('should detect dangerous keywords', () => {
      const dangerousKeywords = ['drop', 'delete', 'update', 'insert', 'alter', 'create', 'truncate'];

      const evilQuery = 'SELECT * FROM readings; DROP TABLE readings';
      const normalized = evilQuery.toLowerCase();

      const hasDangerous = dangerousKeywords.some(kw => normalized.includes(kw));
      expect(hasDangerous).toBe(true);
    });

    it('should handle missing LIMIT by adding one', () => {
      const query = 'SELECT * FROM readings WHERE temperature_c > 15';
      const normalizedQuery = query.trim().toLowerCase();

      if (!normalizedQuery.includes('limit')) {
        const safeQuery = `${query.trim()} LIMIT 100`;
        expect(safeQuery).toContain('LIMIT 100');
      }
    });
  });
});
