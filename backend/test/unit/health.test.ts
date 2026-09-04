import { describe, it, expect, afterAll } from 'vitest';
import { buildApp } from '../../src/app.js';

const mockConfig = {
  DATABASE_URL: 'postgres://dummy',
  INGEST_API_KEY: 'test-key',
  PORT: 3000,
  HOST: '0.0.0.0',
  LOG_LEVEL: 'silent' as const,
  NODE_ENV: 'test' as const,
};

const mockSql = Object.assign(
  (...args: any[]) => Promise.resolve([{ '?column?': 1 }]),
  { begin: () => Promise.resolve(), end: () => Promise.resolve() }
);

const mockHasPendingMigrations = () => Promise.resolve(false);

function buildUnitApp(options?: { sql?: any; hasPendingMigrations?: () => Promise<boolean> }) {
  return buildApp({
    config: mockConfig,
    sql: options?.sql ?? mockSql,
    hasPendingMigrations: options?.hasPendingMigrations ?? mockHasPendingMigrations,
  });
}

describe('GET /up', () => {
  it('returns ok without touching the database', async () => {
    const app = buildUnitApp();
    const res = await app.inject({ method: 'GET', url: '/up' });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.body)).toEqual({ status: 'ok' });
    await app.close();
  });
});

describe('GET /ready', () => {
  it('returns ready when DB is reachable and no pending migrations', async () => {
    const app = buildUnitApp();
    const res = await app.inject({ method: 'GET', url: '/ready' });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.body)).toEqual({ status: 'ready' });
    await app.close();
  });

  it('returns 503 when database is unreachable', async () => {
    const failingSql = Object.assign(
      (...args: any[]) => Promise.reject(new Error('Connection refused')),
      { begin: () => Promise.resolve(), end: () => Promise.resolve() }
    );
    const app = buildUnitApp({ sql: failingSql });
    const res = await app.inject({ method: 'GET', url: '/ready' });
    expect(res.statusCode).toBe(503);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('not ready');
    expect(body.reason).toBe('database unavailable');
    await app.close();
  });

  it('returns 503 when pending migrations exist', async () => {
    const app = buildUnitApp({ hasPendingMigrations: () => Promise.resolve(true) });
    const res = await app.inject({ method: 'GET', url: '/ready' });
    expect(res.statusCode).toBe(503);
    const body = JSON.parse(res.body);
    expect(body.status).toBe('not ready');
    expect(body.reason).toBe('pending migrations');
    await app.close();
  });
});

describe('GET /v1/hello', () => {
  it('returns compatible hello response', async () => {
    const app = buildUnitApp();
    const res = await app.inject({ method: 'GET', url: '/v1/hello' });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.message).toBe('Hello from Zephyr!');
    expect(body.service).toBe('zephyr');
    expect(body.version).toBe('0.3.0');
    expect(body.environment).toBe('test');
    expect(body.timestamp).toBeDefined();
    await app.close();
  });
});
