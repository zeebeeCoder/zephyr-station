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
  gas_density: number | null;
  pm1: number | null;
  pm25: number | null;
  pm10: number | null;
  wind_speed_ms: number | null;
  battery_v: number | null;
  system_amps: number | null;
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
  'temperature_c', 'humidity_pct', 'pressure_hpa', 'gas_density',
  'pm1', 'pm25', 'pm10', 'wind_speed_ms', 'battery_v', 'system_amps', 'rssi',
]);

// ============================================================================
// SQL Security Utilities
// ============================================================================

/**
 * Allowed tables whitelist.
 * Covers both local DuckDB and postgres_scanner prefixed versions.
 */
const ALLOWED_TABLES = new Set([
  'readings',
  'devices',
  'pg.public.readings',
  'pg.public.devices',
]);

/**
 * Strip SQL comments and trailing semicolons to prevent issues.
 * Handles single-line (--) and multi-line comments.
 */
function stripSqlComments(sql: string): string {
  let result = sql;

  // Remove multi-line comments (iterate for nested comments)
  let prev = '';
  while (prev !== result) {
    prev = result;
    result = result.replace(/\/\*[\s\S]*?\*\//g, ' ');
  }

  // Remove single-line comments (-- to end of line)
  result = result.replace(/--[^\n]*/g, ' ');

  // Normalize whitespace
  result = result.replace(/\s+/g, ' ').trim();

  // Remove trailing semicolon (prevents "; LIMIT 100" syntax error)
  if (result.endsWith(';')) {
    result = result.slice(0, -1).trim();
  }

  return result;
}

/**
 * Extract CTE names from a WITH clause.
 * Returns set of CTE names that should be allowed as table references.
 */
function extractCteNames(sql: string): Set<string> {
  const cteNames = new Set<string>();
  const normalized = sql.toLowerCase();

  if (!normalized.startsWith('with')) {
    return cteNames;
  }

  // Match CTE definitions: "name AS (" pattern
  const ctePattern = /\b([a-z_][a-z0-9_]*)\s+as\s*\(/gi;
  let match;
  while ((match = ctePattern.exec(sql)) !== null) {
    cteNames.add(match[1].toLowerCase());
  }

  return cteNames;
}

/**
 * Check for dangerous keywords OUTSIDE of string literals.
 * This prevents false positives like WHERE name = 'DROP TABLE'
 */
function hasDangerousKeywords(sql: string): { found: boolean; keyword?: string } {
  const keywords = ['drop', 'delete', 'update', 'insert', 'alter', 'create', 'truncate', 'grant', 'revoke'];

  // Remove string literals to avoid false positives
  const withoutStrings = sql
    .replace(/'(?:[^'\\]|\\.)*'/g, "''")  // Single-quoted strings
    .replace(/"(?:[^"\\]|\\.)*"/g, '""')  // Double-quoted identifiers
    .toLowerCase();

  for (const keyword of keywords) {
    // Use word boundary to match whole words only
    const pattern = new RegExp(`\\b${keyword}\\b`);
    if (pattern.test(withoutStrings)) {
      return { found: true, keyword };
    }
  }

  return { found: false };
}

/**
 * Validate that query only references allowed tables.
 * Also accepts CTE names defined in the query itself.
 */
function validateTables(sql: string, cteNames: Set<string> = new Set()): { valid: boolean; table?: string } {
  const normalizedSql = sql.toLowerCase();

  // Match table references after FROM or JOIN
  const tablePattern = /(?:from|join)\s+([a-z_][a-z0-9_.]*)/gi;

  let match;
  while ((match = tablePattern.exec(normalizedSql)) !== null) {
    const tableName = match[1].toLowerCase();
    // Allow base tables, postgres-prefixed tables, and CTE names
    if (!ALLOWED_TABLES.has(tableName) && !cteNames.has(tableName)) {
      return { valid: false, table: tableName };
    }
  }

  return { valid: true };
}

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
   * Execute a raw SELECT query with defense-in-depth security.
   *
   * Security layers:
   * 1. Comment stripping + semicolon removal
   * 2. SELECT/WITH-only check (allows CTEs)
   * 3. Dangerous keyword detection (outside string literals)
   * 4. Table whitelist validation (including CTE names)
   * 5. Auto LIMIT injection (skipped for aggregates without GROUP BY)
   * 6. Query timeout
   *
   * Ultimate backstop: postgres_scanner READ_ONLY attachment
   */
  async executeRawQuery(query: string): Promise<Record<string, unknown>[]> {
    const TIMEOUT_MS = 10_000; // 10 seconds

    // Layer 1: Strip comments and trailing semicolons
    const cleanQuery = stripSqlComments(query);
    const normalizedQuery = cleanQuery.toLowerCase();

    // Layer 2: Must be SELECT or WITH (CTE)
    const isSelect = normalizedQuery.startsWith('select');
    const isCte = normalizedQuery.startsWith('with');
    if (!isSelect && !isCte) {
      throw new Error('Only SELECT queries are allowed. Query must start with SELECT or WITH.');
    }

    // Layer 3: Check for dangerous keywords (outside string literals)
    const keywordCheck = hasDangerousKeywords(cleanQuery);
    if (keywordCheck.found) {
      throw new Error(`Query contains forbidden keyword: ${keywordCheck.keyword}`);
    }

    // Layer 4: Extract CTE names and validate table whitelist
    const cteNames = extractCteNames(cleanQuery);
    const tableCheck = validateTables(cleanQuery, cteNames);
    if (!tableCheck.valid) {
      throw new Error(`Query references forbidden table: ${tableCheck.table}. Allowed tables: readings, devices`);
    }

    // Layer 5: Add LIMIT if not present (skip for pure aggregates)
    let safeQuery = cleanQuery;
    const hasLimit = normalizedQuery.includes('limit');
    const hasGroupBy = normalizedQuery.includes('group by');
    const isAggregateOnly = /\b(count|sum|avg|min|max|corr|stddev|percentile)\s*\(/i.test(cleanQuery) && !hasGroupBy;

    // Only add LIMIT for queries that return multiple rows
    if (!hasLimit && !isAggregateOnly) {
      safeQuery = `${safeQuery} LIMIT 100`;
    }

    // Layer 6: Execute with timeout
    const queryPromise = this.db.query(safeQuery);
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Query timeout exceeded (10s)')), TIMEOUT_MS);
    });

    return Promise.race([queryPromise, timeoutPromise]);
  }
}
