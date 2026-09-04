import fastify from 'fastify';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import type { Sql } from 'postgres';
import type { Config } from './config.js';
import { healthRoutes } from './routes/health.js';
import { helloRoutes } from './routes/hello.js';
import { ingestRoutes } from './routes/ingest.js';
import { widgetRoutes } from './routes/widget.js';
import { historyRoutes } from './routes/history.js';
import {
  BODY_LIMIT_BYTES,
  DEFAULT_RATE_LIMIT_POLICY,
  buildLoggerOptions,
  trustPrivateProxy,
  type LoggerStream,
  type RateLimitPolicy,
} from './security.js';

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
  loggerStream?: LoggerStream;
  rateLimits?: RateLimitPolicy;
}) {
  const rateLimits = options.rateLimits ?? DEFAULT_RATE_LIMIT_POLICY;
  const app = fastify({
    bodyLimit: BODY_LIMIT_BYTES,
    trustProxy: trustPrivateProxy,
    logger: buildLoggerOptions(options.config.LOG_LEVEL, options.loggerStream),
  });

  app.decorate('config', options.config);
  app.decorate('sql', options.sql);
  app.decorate('hasPendingMigrations', options.hasPendingMigrations);

  app.register(helmet, {
    global: true,
    contentSecurityPolicy: false,
    crossOriginResourcePolicy: false,
  });
  app.register(rateLimit, {
    global: true,
    max: rateLimits.public.max,
    timeWindow: rateLimits.public.timeWindow,
  });

  app.setErrorHandler((error, request, reply) => {
    const code = typeof error === 'object' && error !== null && 'code' in error
      ? error.code
      : undefined;
    const statusCode = typeof error === 'object' && error !== null && 'statusCode' in error
      ? error.statusCode
      : undefined;

    if (code === 'FST_ERR_CTP_INVALID_JSON_BODY') {
      reply.status(400).send({ error: 'Invalid JSON body' });
      return;
    }
    if (code === 'FST_ERR_CTP_BODY_TOO_LARGE') {
      reply.status(413).send({ error: 'Payload Too Large' });
      return;
    }
    if (statusCode === 429) {
      reply.status(429).send({ error: 'Too Many Requests' });
      return;
    }
    app.log.error(error);
    reply.status(500).send({ error: 'Internal Server Error' });
  });

  app.register(healthRoutes, { prefix: '' });
  app.register(helloRoutes, { prefix: '/v1' });
  app.register(ingestRoutes, { prefix: '/v1', rateLimit: rateLimits.ingest });
  app.register(widgetRoutes, { prefix: '/v1' });
  app.register(historyRoutes, { prefix: '/v1' });

  return app;
}
