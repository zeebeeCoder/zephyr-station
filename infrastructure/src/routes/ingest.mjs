// Sensor data ingest handler

import { success, error, httpStatus, Logger } from '../lib/index.mjs';
import { getDb } from '../lib/db.mjs';
import { ingestPayloadSchema } from '../lib/schema.mjs';

const logger = new Logger('ingest');

export const handleIngest = async (event) => {
  // Parse body
  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch (err) {
    logger.info('Invalid JSON body');
    return error('Invalid JSON body', httpStatus.BAD_REQUEST);
  }

  // Validate payload
  const result = ingestPayloadSchema.safeParse(body);
  if (!result.success) {
    logger.info('Validation failed', { errors: result.error.issues });
    return error({
      message: 'Validation failed',
      errors: result.error.issues.map(i => ({
        path: i.path.join('.'),
        message: i.message,
      })),
    }, httpStatus.BAD_REQUEST);
  }

  const { device_id, timestamp, readings, meta } = result.data;

  // Insert into database
  const sql = getDb();
  try {
    // Auto-register device if not exists
    await sql`
      INSERT INTO devices (id, name)
      VALUES (${device_id}, ${device_id})
      ON CONFLICT (id) DO NOTHING
    `;

    await sql`
      INSERT INTO readings (
        device_id, recorded_at,
        temperature_c, humidity_pct, pressure_hpa, gas_density,
        pm1, pm25, pm10, wind_speed_ms,
        battery_v, system_amps, rssi
      ) VALUES (
        ${device_id}, ${timestamp},
        ${readings.temperature_c}, ${readings.humidity_pct}, ${readings.pressure_hpa}, ${readings.gas_density ?? null},
        ${readings.pm1 ?? null}, ${readings.pm25}, ${readings.pm10}, ${readings.wind_speed_ms ?? null},
        ${meta.battery_v}, ${meta.system_amps ?? null}, ${meta.rssi}
      )
    `;

    logger.info('Reading inserted', { device_id, timestamp });

    return success({
      status: 'ok',
      device_id,
      timestamp,
    });
  } catch (err) {
    logger.error('Database insert failed', { error: err.message });
    return error('Database error', httpStatus.INTERNAL_ERROR);
  }
};
