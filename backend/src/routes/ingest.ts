import { FastifyInstance } from 'fastify';
import { verifyApiKey } from '../auth.js';
import { ingestPayloadSchema } from '../lib/schema.js';
import type { RateLimitRule } from '../security.js';

type IngestRouteOptions = {
  rateLimit: RateLimitRule;
};

export async function ingestRoutes(app: FastifyInstance, options: IngestRouteOptions) {
  app.post('/ingest', {
    config: { rateLimit: options.rateLimit },
    preHandler: verifyApiKey,
  }, async (request, reply) => {
    let body: unknown;
    try {
      body = typeof request.body === 'string' ? JSON.parse(request.body) : request.body;
    } catch {
      reply.status(400).send({ error: 'Invalid JSON body' });
      return;
    }

    const result = ingestPayloadSchema.safeParse(body);
    if (!result.success) {
      reply.status(400).send({
        error: {
          message: 'Validation failed',
          errors: result.error.issues.map((i) => ({
            path: i.path.join('.'),
            message: i.message,
          })),
        },
      });
      return;
    }

    const { device_id, timestamp, readings, meta } = result.data;
    const sql = app.sql;

    try {
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
        ON CONFLICT (device_id, recorded_at) DO NOTHING
      `;

      app.log.info({ device_id, timestamp }, 'Reading inserted');

      return {
        status: 'ok',
        device_id,
        timestamp,
      };
    } catch (err) {
      app.log.error(err, 'Database insert failed');
      reply.status(500).send({ error: 'Database error' });
    }
  });
}
