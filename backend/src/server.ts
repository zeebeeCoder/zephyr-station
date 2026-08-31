import { buildApp } from './app.js';
import { config } from './config.js';
import { getDb, closeDb } from './db.js';
import { runMigrations, hasPendingMigrations } from './db/migrate.js';
import {
  StartupRetryAbortedError,
  StartupRetryExhaustedError,
  retryTransientStartup,
  startupFailureLogDetails,
} from './db/startup-retry.js';

const PORT = config.PORT;
const HOST = config.HOST;

async function start() {
  const sql = getDb();
  const app = buildApp({ config, sql, hasPendingMigrations });

  const startupAbort = new AbortController();
  const abortStartup = () => startupAbort.abort();
  process.once('SIGTERM', abortStartup);
  process.once('SIGINT', abortStartup);

  try {
    await retryTransientStartup({
      operation: () => runMigrations(config.DATABASE_URL),
      signal: startupAbort.signal,
      onRetry: (event) => {
        app.log.warn(event, 'Database unavailable during startup; retrying migrations');
      },
    });
    app.log.info('Migrations applied');
  } catch (err) {
    if (err instanceof StartupRetryAbortedError) {
      app.log.info('Startup cancelled by shutdown signal');
      await app.close();
      await closeDb();
      return;
    }

    const details = startupFailureLogDetails(err);
    if (err instanceof StartupRetryExhaustedError) {
      app.log.error(details, 'Database startup retry budget exhausted; refusing to start');
    } else {
      app.log.error(details, 'Migration failed with a non-transient error; refusing to start');
    }
    await app.close();
    await closeDb();
    process.exitCode = 1;
    return;
  } finally {
    process.removeListener('SIGTERM', abortStartup);
    process.removeListener('SIGINT', abortStartup);
  }

  let closing = false;
  const closeGracefully = async (signal: string) => {
    if (closing) {
      return;
    }
    closing = true;
    app.log.info(`Received ${signal}, closing gracefully`);
    await app.close();
    await closeDb();
    process.exit(0);
  };

  process.once('SIGTERM', () => closeGracefully('SIGTERM'));
  process.once('SIGINT', () => closeGracefully('SIGINT'));

  try {
    await app.listen({ port: PORT, host: HOST });
    app.log.info(`Server listening on http://${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

start();
