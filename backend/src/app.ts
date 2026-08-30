import fastify from 'fastify';
import type { Sql } from 'postgres';
import type { Config } from './config.js';
import { healthRoutes } from './routes/health.js';
import { helloRoutes } from './routes/hello.js';
import { ingestRoutes } from './routes/ingest.js';
import { widgetRoutes } from './routes/widget.js';
import { historyRoutes } from './routes/history.js';

declare module 'fastify' {
  interface FastifyInstance {
    config: Config;
    sql: Sql;
    hasPendingMigrations: (url: string) => Promise<boolean>;
  }
}

export function buildApp(options: {
  config: Config;
  sql: Sql;
  hasPendingMigrations: (url: string) => Promise<boolean>;
}) {
  const app = fastify({
    logger: {
      level: options.config.LOG_LEVEL,
    },
  });

  app.decorate('config', options.config);
  app.decorate('sql', options.sql);
  app.decorate('hasPendingMigrations', options.hasPendingMigrations);

  app.setErrorHandler((error, request, reply) => {
    if (error instanceof Error && 'code' in error && error.code === 'FST_ERR_CTP_INVALID_JSON_BODY') {
      reply.status(400).send({ error: 'Invalid JSON body' });
      return;
    }
    app.log.error(error);
    reply.status(500).send({ error: 'Internal Server Error' });
  });

  app.register(healthRoutes, { prefix: '' });
  app.register(helloRoutes, { prefix: '/v1' });
  app.register(ingestRoutes, { prefix: '/v1' });
  app.register(widgetRoutes, { prefix: '/v1' });
  app.register(historyRoutes, { prefix: '/v1' });

  return app;
}
