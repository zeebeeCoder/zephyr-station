// Zod schemas for API validation

import { z } from 'zod';

// Readings sub-schema
const readingsSchema = z.object({
  temperature_c: z.number().min(-50).max(60),
  humidity_pct: z.number().min(0).max(100),
  pressure_hpa: z.number().min(800).max(1200),
  gas_density: z.number().min(0).max(1000).optional(),
  pm1: z.number().int().min(0).max(1000).optional(),
  pm25: z.number().int().min(0).max(1000),
  pm10: z.number().int().min(0).max(1000),
  wind_speed_ms: z.number().min(0).max(100).optional(),
});

// Meta sub-schema
const metaSchema = z.object({
  battery_v: z.number().min(2.5).max(4.5),
  system_amps: z.number().min(0).max(5).optional(),
  rssi: z.number().int().min(-120).max(0),
});

// Main ingest payload schema
export const ingestPayloadSchema = z.object({
  device_id: z.string().min(1).max(64),
  timestamp: z.string().datetime(),
  readings: readingsSchema,
  meta: metaSchema,
});
