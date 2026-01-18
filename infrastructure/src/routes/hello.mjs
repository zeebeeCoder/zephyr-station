// Health check handler

import { config, success, Logger } from '../lib/index.mjs';

const logger = new Logger('hello');

export const handleHello = async (event) => {
  logger.info('Health check');

  return success({
    message: 'Hello from Zephyr!',
    service: config.serviceName,
    version: config.version,
    environment: config.environment,
    timestamp: new Date().toISOString(),
  });
};
