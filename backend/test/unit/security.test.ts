import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildApp } from '../../src/app.js';
import {
  BODY_LIMIT_BYTES,
  DEFAULT_RATE_LIMIT_POLICY,
  LOGGER_REDACT_PATHS,
  buildLoggerOptions,
  type LoggerStream,
  type RateLimitPolicy,
} from '../../src/security.js';

const API_KEY = 'test-key';
const validPayload = {
  device_id: 'security-test',
  timestamp: '2026-08-31T07:00:00.000Z',
  readings: {
    temperature_c: 22.5,
    humidity_pct: 65,
    pressure_hpa: 1013,
    pm25: 12,
    pm10: 18,
  },
  meta: {
    battery_v: 3.92,
    rssi: -65,
  },
};

const mockConfig = {
  DATABASE_URL: 'postgres://dummy',
  INGEST_API_KEY: API_KEY,
  PORT: 3000,
  HOST: '0.0.0.0',
  LOG_LEVEL: 'silent' as const,
  NODE_ENV: 'test' as const,
};

function createMockSql() {
  return Object.assign(
    vi.fn(async () => []),
    { begin: vi.fn(async () => undefined), end: vi.fn(async () => undefined) },
  );
}

function buildSecurityApp(options?: {
  sql?: any;
  loggerStream?: LoggerStream;
  logLevel?: 'silent' | 'info';
  rateLimits?: RateLimitPolicy;
}) {
  return buildApp({
    config: { ...mockConfig, LOG_LEVEL: options?.logLevel ?? 'silent' },
    sql: options?.sql ?? createMockSql(),
    hasPendingMigrations: async () => false,
    loggerStream: options?.loggerStream,
    rateLimits: options?.rateLimits,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ingest authentication', () => {
  it('preserves the generic 403 contract for missing and wrong keys without database work', async () => {
    const sql = createMockSql();
    const app = buildSecurityApp({ sql });

    for (const headers of [
      { 'content-type': 'application/json' },
      { 'content-type': 'application/json', 'x-api-key': 'wrong-key' },
    ]) {
      const response = await app.inject({
        method: 'POST',
        url: '/v1/ingest',
        headers,
        body: JSON.stringify(validPayload),
      });

      expect(response.statusCode).toBe(403);
      expect(JSON.parse(response.body)).toEqual({ error: 'Forbidden' });
      expect(response.body).not.toContain(API_KEY);
    }

    expect(sql).not.toHaveBeenCalled();
    await app.close();
  });

  it('preserves the successful ingest response contract for the correct key', async () => {
    const sql = createMockSql();
    const app = buildSecurityApp({ sql });
    const response = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'content-type': 'application/json', 'x-api-key': API_KEY },
      body: JSON.stringify(validPayload),
    });

    expect(response.statusCode).toBe(200);
    expect(JSON.parse(response.body)).toEqual({
      status: 'ok',
      device_id: validPayload.device_id,
      timestamp: validPayload.timestamp,
    });
    expect(sql).toHaveBeenCalledTimes(2);
    await app.close();
  });
});

describe('request body limit', () => {
  it('rejects a body over 4 KiB with 413 before database work', async () => {
    const sql = createMockSql();
    const app = buildSecurityApp({ sql });
    const oversizedBody = JSON.stringify({ padding: 'x'.repeat(BODY_LIMIT_BYTES) });

    const response = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'content-type': 'application/json', 'x-api-key': API_KEY },
      body: oversizedBody,
    });

    expect(Buffer.byteLength(oversizedBody)).toBeGreaterThan(BODY_LIMIT_BYTES);
    expect(response.statusCode).toBe(413);
    expect(JSON.parse(response.body)).toEqual({ error: 'Payload Too Large' });
    expect(sql).not.toHaveBeenCalled();
    await app.close();
  });
});

describe('rate limiting', () => {
  it('returns 429 with reset headers, resets by clock, and isolates ingest from public reads', async () => {
    let now = 1_000;
    vi.spyOn(Date, 'now').mockImplementation(() => now);

    const rateLimits: RateLimitPolicy = {
      public: { max: 2, timeWindow: 1_000 },
      ingest: { max: 3, timeWindow: 1_000 },
    };
    const app = buildSecurityApp({ rateLimits });

    expect((await app.inject({ method: 'GET', url: '/up' })).statusCode).toBe(200);
    expect((await app.inject({ method: 'GET', url: '/v1/hello' })).statusCode).toBe(200);

    const limitedRead = await app.inject({ method: 'GET', url: '/up' });
    expect(limitedRead.statusCode).toBe(429);
    expect(JSON.parse(limitedRead.body)).toEqual({ error: 'Too Many Requests' });
    expect(limitedRead.headers['x-ratelimit-limit']).toBe('2');
    expect(limitedRead.headers['x-ratelimit-remaining']).toBe('0');
    expect(limitedRead.headers['x-ratelimit-reset']).toBe('1');
    expect(limitedRead.headers['retry-after']).toBe('1');

    for (let index = 0; index < 3; index += 1) {
      const ingest = await app.inject({
        method: 'POST',
        url: '/v1/ingest',
        headers: { 'content-type': 'application/json', 'x-api-key': API_KEY },
        body: JSON.stringify(validPayload),
      });
      expect(ingest.statusCode).toBe(200);
    }

    const limitedIngest = await app.inject({
      method: 'POST',
      url: '/v1/ingest',
      headers: { 'content-type': 'application/json', 'x-api-key': API_KEY },
      body: JSON.stringify(validPayload),
    });
    expect(limitedIngest.statusCode).toBe(429);
    expect(limitedIngest.headers['x-ratelimit-limit']).toBe('3');

    now += 1_001;
    const resetRead = await app.inject({ method: 'GET', url: '/up' });
    expect(resetRead.statusCode).toBe(200);
    expect(resetRead.headers['x-ratelimit-remaining']).toBe('1');

    await app.close();
  });

  it('keeps production limits above the complete eight-reading device replay buffer', () => {
    expect(DEFAULT_RATE_LIMIT_POLICY).toEqual({
      public: { max: 60, timeWindow: 60_000 },
      ingest: { max: 120, timeWindow: 60_000 },
    });
    expect(DEFAULT_RATE_LIMIT_POLICY.ingest.max).toBeGreaterThan(8);
  });
});

describe('security headers and proxy trust', () => {
  it('sets API-compatible security headers without changing the response body', async () => {
    const app = buildSecurityApp();
    const response = await app.inject({ method: 'GET', url: '/up' });

    expect(response.statusCode).toBe(200);
    expect(JSON.parse(response.body)).toEqual({ status: 'ok' });
    expect(response.headers['x-content-type-options']).toBe('nosniff');
    expect(response.headers['x-frame-options']).toBe('SAMEORIGIN');
    expect(response.headers['strict-transport-security']).toContain('max-age=31536000');
    expect(response.headers['referrer-policy']).toBe('no-referrer');
    expect(response.headers['content-security-policy']).toBeUndefined();
    expect(response.headers['cross-origin-resource-policy']).toBeUndefined();

    await app.close();
  });

  it('trusts one private proxy hop and ignores XFF on direct public sockets', async () => {
    const app = buildSecurityApp();
    app.get('/_test/ip', { config: { rateLimit: false } }, async (request) => ({ ip: request.ip }));

    // kamal-proxy sanitizes inbound forwarding headers and sends one observed client address.
    const sanitizedProxyRequest = await app.inject({
      method: 'GET',
      url: '/_test/ip',
      remoteAddress: '172.18.0.2',
      headers: { 'x-forwarded-for': '203.0.113.8' },
    });
    expect(JSON.parse(sanitizedProxyRequest.body)).toEqual({ ip: '203.0.113.8' });

    // Defense in depth: if a private proxy passed a chain, Fastify accepts only its nearest client hop.
    const forwardedChain = await app.inject({
      method: 'GET',
      url: '/_test/ip',
      remoteAddress: '172.18.0.2',
      headers: { 'x-forwarded-for': '198.51.100.77, 192.168.20.25' },
    });
    expect(JSON.parse(forwardedChain.body)).toEqual({ ip: '192.168.20.25' });

    const direct = await app.inject({
      method: 'GET',
      url: '/_test/ip',
      remoteAddress: '198.51.100.50',
      headers: { 'x-forwarded-for': '203.0.113.8' },
    });
    expect(JSON.parse(direct.body)).toEqual({ ip: '198.51.100.50' });

    await app.close();
  });
});

describe('log redaction', () => {
  it('configures and applies redaction without leaking sensitive request values', async () => {
    const chunks: string[] = [];
    const stream = { write: (message: string) => chunks.push(message) };
    const app = buildSecurityApp({ loggerStream: stream, logLevel: 'info' });
    const apiSecret = 'api-secret-must-not-appear';
    const authorizationSecret = 'authorization-secret-must-not-appear';
    const cookieSecret = 'cookie-secret-must-not-appear';
    const setCookieSecret = 'set-cookie-secret-must-not-appear';

    const loggerOptions = buildLoggerOptions('info');
    expect(loggerOptions.redact.paths).toEqual(LOGGER_REDACT_PATHS);

    app.log.info({
      headers: {
        'x-api-key': apiSecret,
        authorization: authorizationSecret,
        cookie: cookieSecret,
      },
      responseHeaders: { 'set-cookie': setCookieSecret },
    }, 'redaction probe');

    const response = await app.inject({
      method: 'GET',
      url: '/up',
      headers: {
        'x-api-key': apiSecret,
        authorization: authorizationSecret,
        cookie: cookieSecret,
      },
    });
    await app.close();

    const capturedLogs = chunks.join('');
    expect(capturedLogs).toContain('[REDACTED]');
    for (const secret of [apiSecret, authorizationSecret, cookieSecret, setCookieSecret]) {
      expect(capturedLogs).not.toContain(secret);
      expect(response.body).not.toContain(secret);
    }
  });
});
