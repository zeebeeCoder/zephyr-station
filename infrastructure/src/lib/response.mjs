// Response helpers - demonstrates function exports

import { httpStatus } from './config.mjs';

export const json = (body, statusCode = httpStatus.OK) => ({
  statusCode,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const success = (data) => json(data, httpStatus.OK);

export const error = (message, statusCode = httpStatus.INTERNAL_ERROR) =>
  json({ error: message }, statusCode);
