import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import postgres from 'postgres';

const MIGRATIONS_DIR = new URL('./migrations', import.meta.url).pathname;

export async function runMigrations(databaseUrl: string) {
  const sql = postgres(databaseUrl, {
    max: 1,
    connect_timeout: 2,
  });

  try {
    await sql`
      CREATE TABLE IF NOT EXISTS schema_migrations (
        filename TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `;

    const applied = new Set(
      (await sql<{ filename: string }[]>`SELECT filename FROM schema_migrations`).map((r) => r.filename)
    );

    const files = (await readdir(MIGRATIONS_DIR))
      .filter((f) => f.endsWith('.sql'))
      .sort();

    for (const file of files) {
      if (applied.has(file)) {
        console.log(`  ✓ ${file} (already applied)`);
        continue;
      }

      const content = await readFile(join(MIGRATIONS_DIR, file), 'utf-8');
      await sql.begin(async (tx) => {
        await tx.unsafe(content);
        await tx`INSERT INTO schema_migrations (filename) VALUES (${file})`;
      });
      console.log(`  ✓ ${file} (applied)`);
    }

    console.log('Migrations complete.');
  } finally {
    await sql.end();
  }
}

export async function hasPendingMigrations(databaseUrl: string): Promise<boolean> {
  const sql = postgres(databaseUrl, {
    max: 1,
    connect_timeout: 10,
  });

  try {
    const applied = await sql`
      SELECT filename FROM schema_migrations
    `;
    const appliedSet = new Set(applied.map((r) => r.filename));

    const files = (await readdir(MIGRATIONS_DIR))
      .filter((f) => f.endsWith('.sql'))
      .sort();

    return files.some((f) => !appliedSet.has(f));
  } catch (err) {
    // If schema_migrations doesn't exist, there are pending migrations
    if (err instanceof Error && err.message.includes('schema_migrations')) {
      return true;
    }
    throw err;
  } finally {
    await sql.end();
  }
}

// CLI entrypoint
if (import.meta.url === `file://${process.argv[1]}`) {
  const url = process.env.DATABASE_URL;
  if (!url) {
    console.error('DATABASE_URL not set');
    process.exit(1);
  }
  runMigrations(url).catch(() => {
    console.error('Migration failed');
    process.exit(1);
  });
}
