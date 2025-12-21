import { tool } from 'ai';
import { z } from 'zod';
import { getDbClient } from '@/lib/db/client';
import { ReadingsRepository, type Reading, type PeriodStats } from '@/lib/db/repositories/readings';

// ============================================================================
// Helpers
// ============================================================================

// Convert BigInt values to numbers for JSON serialization
// DuckDB returns COUNT(*) and some integers as BigInt
function serializeBigInts<T>(obj: T): T {
  return JSON.parse(
    JSON.stringify(obj, (_key, value) =>
      typeof value === 'bigint' ? Number(value) : value
    )
  );
}

// ============================================================================
// Schemas
// ============================================================================

const getCurrentSchema = z.object({
  device_id: z.string().optional().describe('Specific device ID (defaults to all devices)'),
});

const queryRangeSchema = z.object({
  start: z.string().describe('Start time in ISO 8601 format (e.g., 2024-01-15T00:00:00Z)'),
  end: z.string().describe('End time in ISO 8601 format (e.g., 2024-01-15T23:59:59Z)'),
  device_id: z.string().optional().describe('Specific device ID (defaults to all devices)'),
  metrics: z.array(z.string()).optional().describe('Specific metrics to return (e.g., ["temperature_c", "humidity_pct"])'),
  limit: z.number().optional().default(100).describe('Maximum number of readings to return (default 100)'),
});

const comparePeriodsSchema = z.object({
  period1_start: z.string().describe('Start of first period (ISO 8601)'),
  period1_end: z.string().describe('End of first period (ISO 8601)'),
  period2_start: z.string().describe('Start of second period (ISO 8601)'),
  period2_end: z.string().describe('End of second period (ISO 8601)'),
  device_id: z.string().optional().describe('Specific device ID (defaults to all devices)'),
});

const executeSqlSchema = z.object({
  query: z.string().describe('SQL SELECT query to execute'),
});

// ============================================================================
// Repository Factory
// ============================================================================

function getRepository(): ReadingsRepository {
  return new ReadingsRepository(getDbClient());
}

// ============================================================================
// Tool: Get Current Readings
// ============================================================================

export const getCurrentReadings = tool({
  description: 'Get the latest/current weather readings from the station. Returns the most recent sensor data.',
  inputSchema: getCurrentSchema,
  execute: async ({ device_id }): Promise<Reading[]> => {
    const repo = getRepository();
    const results = await repo.getLatest(device_id);
    return serializeBigInts(results);
  },
});

// ============================================================================
// Tool: Query Time Range
// ============================================================================

export const queryTimeRange = tool({
  description: 'Query weather readings within a specific time range. Returns readings between start and end times.',
  inputSchema: queryRangeSchema,
  execute: async ({ start, end, device_id, metrics, limit }): Promise<Reading[]> => {
    const repo = getRepository();
    const results = await repo.queryRange(start, end, {
      deviceId: device_id,
      metrics,
      limit,
    });
    return serializeBigInts(results);
  },
});

// ============================================================================
// Tool: Compare Periods
// ============================================================================

export const comparePeriods = tool({
  description: 'Compare weather statistics between two time periods. Useful for "today vs yesterday" or week-over-week comparisons.',
  inputSchema: comparePeriodsSchema,
  execute: async ({ period1_start, period1_end, period2_start, period2_end, device_id }): Promise<{ period1: PeriodStats; period2: PeriodStats }> => {
    const repo = getRepository();

    const [period1, period2] = await Promise.all([
      repo.getPeriodStats(period1_start, period1_end, 'period1', device_id),
      repo.getPeriodStats(period2_start, period2_end, 'period2', device_id),
    ]);

    return serializeBigInts({ period1, period2 });
  },
});

// ============================================================================
// Tool: Execute Raw SQL (Guarded)
// ============================================================================

export const executeSql = tool({
  description: 'Execute a custom SQL query against the weather database. Only SELECT queries are allowed. Use for complex queries not covered by other tools.',
  inputSchema: executeSqlSchema,
  execute: async ({ query }): Promise<Record<string, unknown>[]> => {
    const repo = getRepository();
    const results = await repo.executeRawQuery(query);
    return serializeBigInts(results);
  },
});

// ============================================================================
// Export all tools
// ============================================================================

export const weatherTools = {
  get_current: getCurrentReadings,
  query_range: queryTimeRange,
  compare_periods: comparePeriods,
  execute_sql: executeSql,
};
