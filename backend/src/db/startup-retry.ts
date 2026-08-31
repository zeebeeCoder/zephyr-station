const TRANSIENT_CONNECTION_CODES = new Set([
  'ECONNABORTED',
  'ECONNREFUSED',
  'ECONNRESET',
  'EHOSTUNREACH',
  'ENETDOWN',
  'ENETUNREACH',
  'EPIPE',
  'ETIMEDOUT',
  'EAI_AGAIN',
  'CONNECT_TIMEOUT', // postgres.js connection timeout
  'CONNECTION_CLOSED', // postgres.js socket closed during a query
  'CONNECTION_DESTROYED', // postgres.js socket destroyed during a query
  '08001', // PostgreSQL: unable to establish SQL connection
  '08006', // PostgreSQL: connection failure
  '57P03', // PostgreSQL: cannot connect now (for example, startup/recovery)
]);

export type StartupRetryPolicy = {
  delaysMs: readonly number[];
  maxElapsedMs: number;
};

export const STARTUP_RETRY_POLICY: StartupRetryPolicy = {
  delaysMs: [250, 500, 1_000],
  maxElapsedMs: 12_000,
};

export type StartupRetryEvent = {
  attempt: number;
  maxAttempts: number;
  delayMs: number;
  code: string;
};

export class StartupRetryExhaustedError extends Error {
  readonly attempts: number;
  readonly maxAttempts: number;
  readonly elapsedMs: number;
  readonly code: string;

  constructor(options: {
    cause: unknown;
    attempts: number;
    maxAttempts: number;
    elapsedMs: number;
    code: string;
  }) {
    super('Database startup retry budget exhausted', { cause: options.cause });
    this.name = 'StartupRetryExhaustedError';
    this.attempts = options.attempts;
    this.maxAttempts = options.maxAttempts;
    this.elapsedMs = options.elapsedMs;
    this.code = options.code;
  }
}

export class StartupRetryAbortedError extends Error {
  constructor() {
    super('Database startup retry aborted');
    this.name = 'StartupRetryAbortedError';
  }
}

function objectProperty(value: object, property: string): unknown {
  return (value as Record<string, unknown>)[property];
}

function findConnectionErrorCode(error: unknown, seen: Set<object>): string | undefined {
  if (typeof error !== 'object' || error === null || seen.has(error)) {
    return undefined;
  }
  seen.add(error);

  const code = objectProperty(error, 'code');
  if (typeof code === 'string') {
    return code;
  }

  const causeCode = findConnectionErrorCode(objectProperty(error, 'cause'), seen);
  if (causeCode) {
    return causeCode;
  }

  const errors = objectProperty(error, 'errors');
  if (Array.isArray(errors)) {
    for (const nestedError of errors) {
      const nestedCode = findConnectionErrorCode(nestedError, seen);
      if (nestedCode) {
        return nestedCode;
      }
    }
  }

  return undefined;
}

export function connectionErrorCode(error: unknown): string | undefined {
  return findConnectionErrorCode(error, new Set());
}

export function isTransientConnectionError(error: unknown, seen = new Set<object>()): boolean {
  if (typeof error !== 'object' || error === null || seen.has(error)) {
    return false;
  }
  seen.add(error);

  const code = objectProperty(error, 'code');
  const errors = objectProperty(error, 'errors');
  const cause = objectProperty(error, 'cause');
  if (Array.isArray(errors) && errors.length > 0) {
    const allErrorsAreTransient = errors.every(
      (nestedError) => isTransientConnectionError(nestedError, new Set(seen)),
    );
    const causeIsTransient = cause === undefined
      || isTransientConnectionError(cause, new Set(seen));
    const aggregateCodeIsTransient = code === undefined
      || (typeof code === 'string' && TRANSIENT_CONNECTION_CODES.has(code));
    return allErrorsAreTransient && causeIsTransient && aggregateCodeIsTransient;
  }

  if (typeof code === 'string') {
    return TRANSIENT_CONNECTION_CODES.has(code);
  }

  return cause !== undefined && isTransientConnectionError(cause, seen);
}

function assertValidPolicy(policy: StartupRetryPolicy): void {
  if (!Number.isFinite(policy.maxElapsedMs) || policy.maxElapsedMs <= 0) {
    throw new TypeError('Startup retry maxElapsedMs must be positive');
  }
  if (policy.delaysMs.some((delay) => !Number.isFinite(delay) || delay < 0)) {
    throw new TypeError('Startup retry delays must be non-negative');
  }
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    throw new StartupRetryAbortedError();
  }
}

async function sleepWithSignal(delayMs: number, signal?: AbortSignal): Promise<void> {
  throwIfAborted(signal);

  await new Promise<void>((resolve, reject) => {
    const onAbort = () => {
      clearTimeout(timer);
      reject(new StartupRetryAbortedError());
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, delayMs);

    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

export async function retryTransientStartup<T>(options: {
  operation: (attempt: number) => Promise<T>;
  policy?: StartupRetryPolicy;
  sleep?: (delayMs: number, signal?: AbortSignal) => Promise<void>;
  now?: () => number;
  signal?: AbortSignal;
  onRetry?: (event: StartupRetryEvent) => void;
}): Promise<T> {
  const policy = options.policy ?? STARTUP_RETRY_POLICY;
  const sleep = options.sleep ?? sleepWithSignal;
  const now = options.now ?? Date.now;
  const maxAttempts = policy.delaysMs.length + 1;
  const startedAt = now();

  assertValidPolicy(policy);

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    throwIfAborted(options.signal);

    try {
      const result = await options.operation(attempt);
      throwIfAborted(options.signal);
      return result;
    } catch (error) {
      if (error instanceof StartupRetryAbortedError || options.signal?.aborted) {
        throw new StartupRetryAbortedError();
      }
      if (!isTransientConnectionError(error)) {
        throw error;
      }

      const elapsedMs = Math.max(0, now() - startedAt);
      const delayMs = policy.delaysMs[attempt - 1];
      const code = connectionErrorCode(error) ?? 'UNKNOWN';
      const budgetExhausted = delayMs === undefined
        || elapsedMs + delayMs >= policy.maxElapsedMs;

      if (budgetExhausted) {
        throw new StartupRetryExhaustedError({
          cause: error,
          attempts: attempt,
          maxAttempts,
          elapsedMs,
          code,
        });
      }

      options.onRetry?.({ attempt, maxAttempts, delayMs, code });
      await sleep(delayMs, options.signal);
    }
  }

  throw new Error('Unreachable startup retry state');
}

export function startupFailureLogDetails(error: unknown): Record<string, number | string> {
  const details: Record<string, number | string> = {
    code: connectionErrorCode(error) ?? 'UNKNOWN',
  };

  if (error instanceof StartupRetryExhaustedError) {
    details.attempts = error.attempts;
    details.maxAttempts = error.maxAttempts;
    details.elapsedMs = error.elapsedMs;
  }

  return details;
}
