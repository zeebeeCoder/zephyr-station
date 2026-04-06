// Historical readings handler

import { success, error, httpStatus, Logger } from '../lib/index.mjs';
import { getDb } from '../lib/db.mjs';

const logger = new Logger('history');

const METRICS = {
  temperature_c: { column: 'temperature_c', unit: '°C' },
  pm25:          { column: 'pm25',          unit: 'µg/m³' },
  wind_speed_ms: { column: 'wind_speed_ms', unit: 'm/s' },
};

const RANGES = {
  '24h': { interval: '24 hours', aggregate: false },
  '7d':  { interval: '7 days',   aggregate: true },
  '30d': { interval: '30 days',  aggregate: true },
};

export const handleHistory = async (event) => {
  const params = event.queryStringParameters || {};
  const { device_id, metric, range } = params;

  // Validate
  if (!device_id) {
    return error('Missing device_id', httpStatus.BAD_REQUEST);
  }
  if (!metric || !METRICS[metric]) {
    return error(`Invalid metric. Must be one of: ${Object.keys(METRICS).join(', ')}`, httpStatus.BAD_REQUEST);
  }
  if (!range || !RANGES[range]) {
    return error(`Invalid range. Must be one of: ${Object.keys(RANGES).join(', ')}`, httpStatus.BAD_REQUEST);
  }

  const { column, unit } = METRICS[metric];
  const { interval, aggregate } = RANGES[range];

  const sql = getDb();

  try {
    let rows;

    if (aggregate) {
      // Hourly averages for 7d/30d
      rows = await sql.unsafe(
        `SELECT date_trunc('hour', recorded_at) AS t, AVG(${column})::numeric(6,1) AS v
         FROM readings
         WHERE device_id = $1 AND recorded_at > NOW() - INTERVAL '${interval}'
         GROUP BY 1 ORDER BY 1 ASC`,
        [device_id]
      );
    } else {
      // Raw readings for 24h
      rows = await sql.unsafe(
        `SELECT recorded_at AS t, ${column} AS v
         FROM readings
         WHERE device_id = $1 AND recorded_at > NOW() - INTERVAL '${interval}'
         ORDER BY recorded_at ASC`,
        [device_id]
      );
    }

    const points = rows.map(r => ({
      t: new Date(r.t).toISOString(),
      v: r.v !== null ? Number(r.v) : null,
    })).filter(p => p.v !== null);

    logger.info('History query', { device_id, metric, range, points: points.length });

    return success({
      device_id,
      metric,
      range,
      unit,
      points,
    });
  } catch (err) {
    logger.error('History query failed', { error: err.message });
    return error('Database error', httpStatus.INTERNAL_ERROR);
  }
};
