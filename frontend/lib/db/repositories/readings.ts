import type { DbClient } from '../client';

// ============================================================================
// Types
// ============================================================================

export interface Reading {
  id: number;
  device_id: string;
  recorded_at: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  pressure_hpa: number | null;
  pm25: number | null;
  pm10: number | null;
  wind_speed_ms: number | null;
  wind_dir_deg: number | null;
  battery_v: number | null;
  rssi: number | null;
}

export interface PeriodStats {
  period: string;
  avg_temperature: number | null;
  min_temperature: number | null;
  max_temperature: number | null;
  avg_humidity: number | null;
  avg_pm25: number | null;
  max_pm25: number | null;
  reading_count: number;
}

export interface QueryRangeOptions {
  deviceId?: string;
  metrics?: string[];
  limit?: number;
}

// Allowed columns for metrics selection (whitelist to prevent SQL injection)
const ALLOWED_METRICS = new Set([
  'temperature_c', 'humidity_pct', 'pressure_hpa', 'pm25', 'pm10',
  'wind_speed_ms', 'wind_dir_deg', 'battery_v', 'rssi',
]);

// ============================================================================
// Repository
// ============================================================================

export class ReadingsRepository {
  constructor(private db: DbClient) {}

  /**
   * Get the latest reading(s), optionally filtered by device
   */
  async getLatest(deviceId?: string): Promise<Reading[]> {
    if (deviceId) {
      return this.db.query<Reading>(
        `SELECT * FROM readings WHERE device_id = ? ORDER BY recorded_at DESC LIMIT 1`,
        [deviceId]
      );
    }

    return this.db.query<Reading>(
      `SELECT * FROM readings WHERE recorded_at = (SELECT MAX(recorded_at) FROM readings)`
    );
  }

  /**
   * Query readings within a time range
   */
  async queryRange(
    start: string,
    end: string,
    options: QueryRangeOptions = {}
  ): Promise<Reading[]> {
    const { deviceId, metrics, limit = 100 } = options;

    // Whitelist column names to prevent SQL injection via metrics
    const safeMetrics = metrics?.filter(m => ALLOWED_METRICS.has(m)) || [];
    const columns = safeMetrics.length > 0
      ? ['id', 'device_id', 'recorded_at', ...safeMetrics].join(', ')
      : '*';

    const rowLimit = Math.min(limit, 500); // Cap at 500

    // Build parameterized query
    const params: unknown[] = [start, end];
    let query = `SELECT ${columns} FROM readings WHERE recorded_at >= ? AND recorded_at <= ?`;

    if (deviceId) {
      query += ' AND device_id = ?';
      params.push(deviceId);
    }

    query += ' ORDER BY recorded_at DESC LIMIT ?';
    params.push(rowLimit);

    return this.db.query<Reading>(query, params);
  }

  /**
   * Get aggregated statistics for a time period
   */
  async getPeriodStats(
    start: string,
    end: string,
    label: string,
    deviceId?: string
  ): Promise<PeriodStats> {
    const params: unknown[] = [label, start, end];
    let query = `
      SELECT
        ? as period,
        AVG(temperature_c) as avg_temperature,
        MIN(temperature_c) as min_temperature,
        MAX(temperature_c) as max_temperature,
        AVG(humidity_pct) as avg_humidity,
        AVG(pm25) as avg_pm25,
        MAX(pm25) as max_pm25,
        COUNT(*) as reading_count
      FROM readings
      WHERE recorded_at >= ? AND recorded_at <= ?
    `;

    if (deviceId) {
      query += ' AND device_id = ?';
      params.push(deviceId);
    }

    const results = await this.db.query<PeriodStats>(query, params);
    return results[0];
  }

  /**
   * Execute a raw SELECT query (with safety guards)
   */
  async executeRawQuery(query: string): Promise<Record<string, unknown>[]> {
    // Security: Only allow SELECT queries
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery.startsWith('select')) {
      throw new Error('Only SELECT queries are allowed. Query must start with SELECT.');
    }

    // Security: Block dangerous keywords
    const dangerousKeywords = ['drop', 'delete', 'update', 'insert', 'alter', 'create', 'truncate'];
    for (const keyword of dangerousKeywords) {
      if (normalizedQuery.includes(keyword)) {
        throw new Error(`Query contains forbidden keyword: ${keyword}`);
      }
    }

    // Add LIMIT if not present
    let safeQuery = query.trim();
    if (!normalizedQuery.includes('limit')) {
      safeQuery = `${safeQuery} LIMIT 100`;
    }

    return this.db.query(safeQuery);
  }
}
