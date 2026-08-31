import { describe, expect, it, vi } from 'vitest';
import {
  StartupRetryAbortedError,
  StartupRetryExhaustedError,
  isTransientConnectionError,
  retryTransientStartup,
  startupFailureLogDetails,
  type StartupRetryEvent,
  type StartupRetryPolicy,
} from '../../src/db/startup-retry.js';

const testPolicy: StartupRetryPolicy = {
  delaysMs: [10, 20],
  maxElapsedMs: 100,
};

function codedError(code: string, message = 'connection failed'): Error & { code: string } {
  return Object.assign(new Error(message), { code });
}

describe('retryTransientStartup', () => {
  it('returns immediately when the operation succeeds', async () => {
    const operation = vi.fn(async () => 'ready');
    const sleep = vi.fn(async () => undefined);
    const onRetry = vi.fn();

    await expect(retryTransientStartup({
      operation,
      sleep,
      onRetry,
      policy: testPolicy,
    })).resolves.toBe('ready');

    expect(operation).toHaveBeenCalledOnce();
    expect(operation).toHaveBeenCalledWith(1);
    expect(sleep).not.toHaveBeenCalled();
    expect(onRetry).not.toHaveBeenCalled();
  });

  it('retries nested cause and AggregateError connectivity failures before succeeding', async () => {
    const secretUrl = 'postgres://user:secret-password@database.internal/zephyr';
    const nestedRefusal = new Error(`could not connect to ${secretUrl}`, {
      cause: codedError('ECONNREFUSED'),
    });
    const aggregateFailure = new AggregateError([
      codedError('CONNECT_TIMEOUT'),
      codedError('EAI_AGAIN'),
    ], `connection attempts failed for ${secretUrl}`);
    const operation = vi.fn()
      .mockRejectedValueOnce(nestedRefusal)
      .mockRejectedValueOnce(aggregateFailure)
      .mockResolvedValueOnce('ready');
    const retryEvents: StartupRetryEvent[] = [];
    let now = 0;
    const sleep = vi.fn(async (delayMs: number) => {
      now += delayMs;
    });

    await expect(retryTransientStartup({
      operation,
      sleep,
      now: () => now,
      onRetry: (event) => retryEvents.push(event),
      policy: testPolicy,
    })).resolves.toBe('ready');

    expect(operation).toHaveBeenCalledTimes(3);
    expect(sleep.mock.calls.map(([delayMs]) => delayMs)).toEqual([10, 20]);
    expect(retryEvents).toEqual([
      { attempt: 1, maxAttempts: 3, delayMs: 10, code: 'ECONNREFUSED' },
      { attempt: 2, maxAttempts: 3, delayMs: 20, code: 'CONNECT_TIMEOUT' },
    ]);
    expect(JSON.stringify(retryEvents)).not.toContain(secretUrl);
  });

  it('throws a safe terminal error after exhausting transient attempts', async () => {
    const secretUrl = 'postgres://user:secret-password@database.internal/zephyr';
    const operation = vi.fn(async () => {
      throw codedError('ETIMEDOUT', `timed out connecting to ${secretUrl}`);
    });
    let now = 0;
    const sleep = vi.fn(async (delayMs: number) => {
      now += delayMs;
    });

    let caught: unknown;
    try {
      await retryTransientStartup({
        operation,
        sleep,
        now: () => now,
        policy: testPolicy,
      });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(StartupRetryExhaustedError);
    expect(caught).toMatchObject({
      attempts: 3,
      maxAttempts: 3,
      elapsedMs: 30,
      code: 'ETIMEDOUT',
    });
    expect(operation).toHaveBeenCalledTimes(3);
    expect(sleep.mock.calls.map(([delayMs]) => delayMs)).toEqual([10, 20]);

    const logDetails = startupFailureLogDetails(caught);
    expect(logDetails).toEqual({
      code: 'ETIMEDOUT',
      attempts: 3,
      maxAttempts: 3,
      elapsedMs: 30,
    });
    expect(JSON.stringify(logDetails)).not.toContain(secretUrl);
  });

  it('does not schedule another attempt when the elapsed budget cannot fit its delay', async () => {
    let now = 0;
    const operation = vi.fn(async () => {
      now = 95;
      throw codedError('ECONNREFUSED');
    });
    const sleep = vi.fn(async () => undefined);

    await expect(retryTransientStartup({
      operation,
      sleep,
      now: () => now,
      policy: testPolicy,
    })).rejects.toMatchObject({
      attempts: 1,
      maxAttempts: 3,
      elapsedMs: 95,
      code: 'ECONNREFUSED',
    });

    expect(operation).toHaveBeenCalledOnce();
    expect(sleep).not.toHaveBeenCalled();
  });

  it.each([
    'CONNECT_TIMEOUT',
    'CONNECTION_CLOSED',
    'CONNECTION_DESTROYED',
    '57P03',
  ])('recognizes postgres.js/PostgreSQL transient code %s', (code) => {
    expect(isTransientConnectionError(codedError(code))).toBe(true);
  });

  it.each([
    ['SQL/schema failure', codedError('42P01', 'relation does not exist')],
    ['invalid database URL', codedError('ERR_INVALID_URL', 'invalid URL')],
    ['permanent DNS failure', codedError('ENOTFOUND', 'host not found')],
    ['mixed aggregate', new AggregateError([
      codedError('ECONNREFUSED'),
      codedError('42P01'),
    ])],
    ['transient-coded mixed aggregate', Object.assign(new AggregateError([
      codedError('ECONNREFUSED'),
      codedError('28P01', 'password authentication failed'),
    ]), { code: 'ETIMEDOUT' })],
  ])('fails immediately for %s', async (_label, failure) => {
    const operation = vi.fn(async () => {
      throw failure;
    });
    const sleep = vi.fn(async () => undefined);

    await expect(retryTransientStartup({
      operation,
      sleep,
      policy: testPolicy,
    })).rejects.toBe(failure);

    expect(operation).toHaveBeenCalledOnce();
    expect(sleep).not.toHaveBeenCalled();
    expect(isTransientConnectionError(failure)).toBe(false);
  });

  it('aborts before entering backoff when shutdown is signaled', async () => {
    const controller = new AbortController();
    const operation = vi.fn(async () => {
      throw codedError('ECONNREFUSED');
    });

    await expect(retryTransientStartup({
      operation,
      signal: controller.signal,
      policy: { delaysMs: [10_000], maxElapsedMs: 20_000 },
      onRetry: () => controller.abort(),
    })).rejects.toBeInstanceOf(StartupRetryAbortedError);

    expect(operation).toHaveBeenCalledOnce();
  });
});
