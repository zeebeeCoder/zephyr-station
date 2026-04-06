// Lambda handler - router pattern

import { error, httpStatus, Logger } from './lib/index.mjs';
import { handleHello } from './routes/hello.mjs';
import { handleIngest } from './routes/ingest.mjs';
import { handleHistory } from './routes/history.mjs';

const logger = new Logger('router');

// Route table
const routes = {
  'GET /hello': handleHello,
  'POST /ingest': handleIngest,
  'GET /history': handleHistory,
};

export const handler = async (event) => {
  const method = event.httpMethod;
  const path = event.resource || event.path;

  logger.info('Request received', { method, path });

  const routeKey = `${method} ${path}`;
  const routeHandler = routes[routeKey];

  if (!routeHandler) {
    logger.info('Route not found', { routeKey });
    return error('Not Found', httpStatus.NOT_FOUND);
  }

  try {
    return await routeHandler(event);
  } catch (err) {
    logger.error('Handler error', { route: routeKey, error: err.message });
    return error('Internal Server Error', httpStatus.INTERNAL_ERROR);
  }
};
