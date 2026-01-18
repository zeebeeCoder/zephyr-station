import { Database } from 'duckdb-async';
import { readFileSync } from 'fs';
import { join } from 'path';

export type QueryResult = Record<string, unknown>[];

export interface DbClient {
  query<T = Record<string, unknown>>(
    sql: string,
    params?: unknown[]
  ): Promise<T[]>;
  close(): Promise<void>;
}

/**
 * DuckDB Analytics Client with postgres_scanner support.
 *
 * Uses DuckDB as the unified query engine:
 * - When DATABASE_URL is a postgres:// URL, attaches via postgres_scanner
 * - Otherwise, queries local DuckDB tables
 *
 * Benefits:
 * - Columnar OLAP engine optimized for aggregations
 * - Predicate pushdown to Postgres reduces data transfer
 * - Consistent query behavior between dev and prod
 */
export class DuckDbAnalyticsClient implements DbClient {
  private db: Database | null = null;
  private pgAttached: boolean = false;
  private initPromise: Promise<void> | null = null;

  private async getDb(): Promise<Database> {
    if (!this.db) {
      this.db = await Database.create(':memory:');
      // Install postgres extension (downloads on first use, cached after)
      await this.db.run('INSTALL postgres');
      await this.db.run('LOAD postgres');
    }
    return this.db;
  }

  private async attachPostgres(): Promise<void> {
    if (this.pgAttached) return;

    // Use init promise to prevent concurrent attachment attempts
    if (this.initPromise) {
      await this.initPromise;
      return;
    }

    this.initPromise = (async () => {
      const dbUrl = process.env.DATABASE_URL;
      if (dbUrl?.startsWith('postgres')) {
        const db = await this.getDb();
        await db.run(`ATTACH '${dbUrl}' AS pg (TYPE POSTGRES, READ_ONLY)`);
        this.pgAttached = true;
      }
    })();

    await this.initPromise;
  }

  /**
   * Transform SQL to route to postgres_scanner attached tables.
   * Simple regex replacement: readings -> pg.public.readings
   */
  private routeToPostgres(sql: string): string {
    return sql
      .replace(/\bFROM\s+readings\b/gi, 'FROM pg.public.readings')
      .replace(/\bFROM\s+devices\b/gi, 'FROM pg.public.devices')
      .replace(/\bJOIN\s+readings\b/gi, 'JOIN pg.public.readings')
      .replace(/\bJOIN\s+devices\b/gi, 'JOIN pg.public.devices');
  }

  async query<T = Record<string, unknown>>(
    sql: string,
    params: unknown[] = []
  ): Promise<T[]> {
    const db = await this.getDb();
    await this.attachPostgres();

    const transformedSql = this.pgAttached ? this.routeToPostgres(sql) : sql;
    const result = await db.all(transformedSql, ...params);
    return result as T[];
  }

  async close(): Promise<void> {
    if (this.db) {
      await this.db.close();
      this.db = null;
      this.pgAttached = false;
      this.initPromise = null;
    }
  }
}

/**
 * DuckDB client for local file-based development and seeding.
 * Use this for seed scripts or when you need persistent local storage.
 */
export class DuckDbClient implements DbClient {
  private db: Database | null = null;
  private dbPath: string;

  constructor(dbPath: string = 'local.db') {
    this.dbPath = dbPath;
  }

  private async getDb(): Promise<Database> {
    if (!this.db) {
      this.db = await Database.create(this.dbPath);
    }
    return this.db;
  }

  async query<T = Record<string, unknown>>(
    sql: string,
    params: unknown[] = []
  ): Promise<T[]> {
    const db = await this.getDb();
    const result = await db.all(sql, ...params);
    return result as T[];
  }

  async initSchema(): Promise<void> {
    const db = await this.getDb();
    const schemaPath = join(__dirname, 'schema.sql');
    const schema = readFileSync(schemaPath, 'utf-8');

    // Split by semicolon and execute each statement
    const statements = schema
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0);

    for (const stmt of statements) {
      await db.run(stmt);
    }
  }

  async close(): Promise<void> {
    if (this.db) {
      await this.db.close();
      this.db = null;
    }
  }
}

// Factory function - chooses client based on DATABASE_URL
export function createDbClient(): DbClient {
  const dbUrl = process.env.DATABASE_URL || 'local.db';

  // Use analytics client with postgres_scanner for Supabase
  if (dbUrl.startsWith('postgres')) {
    return new DuckDbAnalyticsClient();
  }

  // Use file-based DuckDB for local development
  return new DuckDbClient(dbUrl);
}

// Singleton instance for app usage
let dbClient: DbClient | null = null;

export function getDbClient(): DbClient {
  if (!dbClient) {
    dbClient = createDbClient();
  }
  return dbClient;
}

// Initialize database schema (DuckDB file-based only)
export async function initializeDatabase(): Promise<void> {
  const client = getDbClient();
  if (client instanceof DuckDbClient) {
    await client.initSchema();
  }
}
