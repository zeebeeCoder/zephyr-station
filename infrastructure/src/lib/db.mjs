// Database client for Supabase PostgreSQL

import postgres from 'postgres';
import { config } from './config.mjs';

let sql = null;

export function getDb() {
  if (!sql) {
    sql = postgres(config.databaseUrl, {
      max: 1,
      idle_timeout: 20,
      connect_timeout: 10,
    });
  }
  return sql;
}
