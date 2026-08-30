import { buildApp } from './app.js';
import { config } from './config.js';
import { getDb, closeDb } from './db.js';
import { runMigrations, hasPendingMigrations } from './db/migrate.js';

const PORT = config.PORT;
const HOST = config.HOST;

async function start() {
  const sql = getDb();
  const app = buildApp({ config, sql, hasPendingMigrations });

  try {
    await runMigrations(config.DATABASE_URL);
    app.log.info('Migrations applied');
  } catch (err) {
    app.log.error(err, 'Migration failed, refusing to start');
    process.exit(1);
  }

  const closeGracefully = async (signal: string) => {
    app.log.info(`Received ${signal}, closing gracefully`);
    await app.close();
    await closeDb();
    process.exit(0);
  };

  process.on('SIGTERM', () => closeGracefully('SIGTERM'));
  process.on('SIGINT', () => closeGracefully('SIGINT'));

  try {
    await app.listen({ port: PORT, host: HOST });
    app.log.info(`Server listening on http://${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

start();
