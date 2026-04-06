// Widget endpoint - returns latest reading for a device

import { success, error, httpStatus, Logger } from '../lib/index.mjs';
import { getDb } from '../lib/db.mjs';

const logger = new Logger('widget');

export const handleWidget = async (event) => {
  const params = event.queryStringParameters || {};
  const { device_id } = params;

  if (!device_id) {
    return error('Missing device_id', httpStatus.BAD_REQUEST);
  }

  const sql = getDb();

  try {
    const rows = await sql`
      SELECT
        device_id,
        recorded_at,
        temperature_c, humidity_pct, pressure_hpa, gas_density,
        pm1, pm25, pm10, wind_speed_ms,
        battery_v, system_amps, rssi
      FROM readings
      WHERE device_id = ${device_id}
      ORDER BY recorded_at DESC
      LIMIT 1
    `;

    if (rows.length === 0) {
      return error('No readings found', httpStatus.NOT_FOUND);
    }

    const r = rows[0];
    const dataAgeSeconds = Math.round((Date.now() - new Date(r.recorded_at).getTime()) / 1000);

    return success({
      device_id: r.device_id,
      recorded_at: r.recorded_at,
      readings: {
        temperature_c: r.temperature_c,
        humidity_pct: r.humidity_pct,
        pressure_hpa: r.pressure_hpa,
        gas_density: r.gas_density,
        pm1: r.pm1,
        pm25: r.pm25,
        pm10: r.pm10,
        wind_speed_ms: r.wind_speed_ms,
      },
      meta: {
        battery_v: r.battery_v,
        system_amps: r.system_amps,
        rssi: r.rssi,
      },
      station_status: dataAgeSeconds < 600 ? 'online' : 'offline',
      data_age_seconds: dataAgeSeconds,
    });
  } catch (err) {
    logger.error('Widget query failed', { error: err.message });
    return error('Database error', httpStatus.INTERNAL_ERROR);
  }
};
