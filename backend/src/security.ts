import { isIP } from 'node:net';

export type LoggerStream = {
  write(message: string): void;
};

export const BODY_LIMIT_BYTES = 4 * 1024;

export type RateLimitRule = {
  max: number;
  timeWindow: number;
};

export type RateLimitPolicy = {
  public: RateLimitRule;
  ingest: RateLimitRule;
};

export const DEFAULT_RATE_LIMIT_POLICY: RateLimitPolicy = {
  public: { max: 60, timeWindow: 60_000 },
  ingest: { max: 120, timeWindow: 60_000 },
};

export const LOGGER_REDACT_PATHS = [
  "req.headers['x-api-key']",
  'req.headers.authorization',
  'req.headers.cookie',
  "res.headers['set-cookie']",
  "headers['x-api-key']",
  'headers.authorization',
  'headers.cookie',
  "headers['set-cookie']",
  "responseHeaders['set-cookie']",
];

export function buildLoggerOptions(
  level: string,
  stream?: LoggerStream,
) {
  return {
    level,
    redact: {
      paths: [...LOGGER_REDACT_PATHS],
      censor: '[REDACTED]',
    },
    ...(stream ? { stream } : {}),
  };
}

function isPrivateIpv4(address: string): boolean {
  const octets = address.split('.').map(Number);
  if (octets.length !== 4 || octets.some((octet) => !Number.isInteger(octet))) {
    return false;
  }

  const [first, second] = octets;
  return first === 10
    || first === 127
    || (first === 169 && second === 254)
    || (first === 172 && second >= 16 && second <= 31)
    || (first === 192 && second === 168);
}

function isPrivateIpv6(address: string): boolean {
  const normalized = address.toLowerCase();
  if (normalized === '::1') {
    return true;
  }

  const firstHextet = Number.parseInt(normalized.split(':', 1)[0], 16);
  if (!Number.isFinite(firstHextet)) {
    return false;
  }

  const isUniqueLocal = (firstHextet & 0xfe00) === 0xfc00;
  const isLinkLocal = (firstHextet & 0xffc0) === 0xfe80;
  return isUniqueLocal || isLinkLocal;
}

export function trustPrivateProxy(address: string, hop: number): boolean {
  if (hop !== 0) {
    return false;
  }

  const mappedIpv4 = address.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/i)?.[1];
  const normalized = mappedIpv4 ?? address;
  const version = isIP(normalized);

  if (version === 4) {
    return isPrivateIpv4(normalized);
  }
  if (version === 6) {
    return isPrivateIpv6(normalized);
  }
  return false;
}
