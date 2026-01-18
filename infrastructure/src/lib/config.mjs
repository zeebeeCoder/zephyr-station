// Configuration module

export const config = {
  serviceName: 'zephyr',
  version: '0.2.0',
  environment: process.env.ENVIRONMENT ?? 'dev',
  databaseUrl: process.env.DATABASE_URL,
};

export const httpStatus = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_ERROR: 500,
};
