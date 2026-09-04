import { FastifyInstance } from 'fastify';

const VERSION = '0.3.0';
const SERVICE = 'zephyr';

export async function helloRoutes(app: FastifyInstance) {
  app.get('/hello', async () => {
    return {
      message: 'Hello from Zephyr!',
      service: SERVICE,
      version: VERSION,
      environment: app.config.NODE_ENV,
      timestamp: new Date().toISOString(),
    };
  });
}
