import { FastifyInstance } from 'fastify';

const METRICS = {
  temperature_c: { column: 'temperature_c', unit: '°C' },
  humidity_pct:  { column: 'humidity_pct',  unit: '%' },
  pressure_hpa:  { column: 'pressure_hpa',  unit: 'hPa' },
  pm25:          { column: 'pm25',          unit: 'µg/m³' },
  pm10:          { column: 'pm10',          unit: 'µg/m³' },
  pm1:           { column: 'pm1',           unit: 'µg/m³' },
  wind_speed_ms: { column: 'wind_speed_ms', unit: 'm/s' },
  gas_density:   { column: 'gas_density',   unit: 'kΩ' },
  battery_v:     { column: 'battery_v',     unit: 'V' },
};

const RANGES = {
  '24h': { interval: '24 hours', aggregate: false },
  '7d':  { interval: '7 days',   aggregate: true },
  '30d': { interval: '30 days',  aggregate: true },
};

export async function historyRoutes(app: FastifyInstance) {
  app.get('/history', async (request, reply) => {
    const { device_id, metric, range } = request.query as {
      device_id?: string;
      metric?: string;
      range?: string;
    };

    if (!device_id) {
      reply.status(400).send({ error: 'Missing device_id' });
      return;
    }
    if (!metric || !METRICS[metric as keyof typeof METRICS]) {
      reply.status(400).send({ error: `Invalid metric. Must be one of: ${Object.keys(METRICS).join(', ')}` });
      return;
    }
    if (!range || !RANGES[range as keyof typeof RANGES]) {
      reply.status(400).send({ error: `Invalid range. Must be one of: ${Object.keys(RANGES).join(', ')}` });
      return;
    }

    const { column, unit } = METRICS[metric as keyof typeof METRICS];
    const { interval, aggregate } = RANGES[range as keyof typeof RANGES];
    const sql = app.sql;

    try {
      let rows;

      if (aggregate) {
        rows = await sql`
          SELECT date_trunc('hour', recorded_at) AS t, AVG(${sql(column)})::numeric(6,1) AS v
          FROM readings
          WHERE device_id = ${device_id} AND recorded_at > NOW() - ${interval}::interval
          GROUP BY 1 ORDER BY 1 ASC
        `;
      } else {
        rows = await sql`
          SELECT recorded_at AS t, ${sql(column)} AS v
          FROM readings
          WHERE device_id = ${device_id} AND recorded_at > NOW() - ${interval}::interval
          ORDER BY recorded_at ASC
        `;
      }

      const points = rows.map(r => ({
        t: new Date(r.t as string).toISOString(),
        v: r.v !== null ? Number(r.v) : null,
      })).filter(p => p.v !== null);

      return {
        device_id,
        metric,
        range,
        unit,
        points,
      };
    } catch (err) {
      app.log.error(err, 'History query failed');
      reply.status(500).send({ error: 'Database error' });
    }
  });
}
