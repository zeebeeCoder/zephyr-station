import { FastifyInstance } from 'fastify';

export async function widgetRoutes(app: FastifyInstance) {
  app.get('/widget', async (request, reply) => {
    const { device_id } = request.query as { device_id?: string };
    const sql = app.sql;

    if (!device_id) {
      reply.status(400).send({ error: 'Missing device_id' });
      return;
    }

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
        reply.status(404).send({ error: 'No readings found' });
        return;
      }

      const r = rows[0];
      const num = (v: unknown) => v != null ? Number(v) : null;
      const dataAgeSeconds = Math.round(
        (Date.now() - new Date(r.recorded_at as string).getTime()) / 1000
      );

      return {
        device_id: r.device_id,
        recorded_at: r.recorded_at,
        readings: {
          temperature_c: num(r.temperature_c),
          humidity_pct: num(r.humidity_pct),
          pressure_hpa: num(r.pressure_hpa),
          gas_density: num(r.gas_density),
          pm1: r.pm1,
          pm25: r.pm25,
          pm10: r.pm10,
          wind_speed_ms: num(r.wind_speed_ms),
        },
        meta: {
          battery_v: num(r.battery_v),
          system_amps: num(r.system_amps),
          rssi: r.rssi,
        },
        station_status: dataAgeSeconds < 600 ? 'online' : 'offline',
        data_age_seconds: dataAgeSeconds,
      };
    } catch (err) {
      app.log.error(err, 'Widget query failed');
      reply.status(500).send({ error: 'Database error' });
    }
  });
}
