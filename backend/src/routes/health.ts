import { FastifyInstance } from 'fastify';

export async function healthRoutes(app: FastifyInstance) {
  app.get('/up', async () => {
    return { status: 'ok' };
  });

  app.get('/ready', async (request, reply) => {
    try {
      const sql = app.sql;
      await sql`SELECT 1`;

      const pending = await app.hasPendingMigrations(app.config.DATABASE_URL);
      if (pending) {
        return reply.status(503).send({ status: 'not ready', reason: 'pending migrations' });
      }

      return { status: 'ready' };
    } catch (err) {
      app.log.error(err, 'Ready check failed');
      return reply.status(503).send({ status: 'not ready', reason: 'database unavailable' });
    }
  });
}
