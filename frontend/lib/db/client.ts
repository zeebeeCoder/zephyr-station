import { Database } from 'duckdb-async';
import postgres from 'postgres';
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

// DuckDB client for local development
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

// Postgres client for production
class PostgresClient implements DbClient {
  private sql: postgres.Sql;

  constructor(connectionString: string) {
    this.sql = postgres(connectionString, {
      max: 10,
      idle_timeout: 20,
    });
  }

  async query<T = Record<string, unknown>>(
    sql: string,
    params: unknown[] = []
  ): Promise<T[]> {
    // Use parameterized queries for security
    // postgres.js uses $1, $2, etc. for parameters
    if (params.length === 0) {
      const result = await this.sql.unsafe(sql);
      return result as unknown as T[];
    }

    // Convert ? placeholders to $1, $2, etc. for postgres.js
    let paramIndex = 0;
    const pgSql = sql.replace(/\?/g, () => `$${++paramIndex}`);
    // Cast params to satisfy postgres.js types - values are validated at runtime
    const result = await this.sql.unsafe(pgSql, params as (string | number | boolean | null)[]);
    return result as unknown as T[];
  }

  async close(): Promise<void> {
    await this.sql.end();
  }
}

// Factory function to create appropriate client
export function createDbClient(): DbClient {
  const isDev = process.env.NODE_ENV !== 'production';
  const dbUrl = process.env.DATABASE_URL || 'local.db';

  if (isDev || !dbUrl.startsWith('postgres')) {
    return new DuckDbClient(dbUrl);
  }

  return new PostgresClient(dbUrl);
}

// Singleton instance for app usage
let dbClient: DbClient | null = null;

export function getDbClient(): DbClient {
  if (!dbClient) {
    dbClient = createDbClient();
  }
  return dbClient;
}

// Initialize database schema (DuckDB only)
export async function initializeDatabase(): Promise<void> {
  const client = getDbClient();
  if (client instanceof DuckDbClient) {
    await client.initSchema();
  }
}
