-- Initial schema for Zephyr weather station backend

CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  location TEXT,
  installed_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS readings (
  id SERIAL PRIMARY KEY,
  device_id TEXT NOT NULL REFERENCES devices(id),
  recorded_at TIMESTAMPTZ NOT NULL,
  temperature_c NUMERIC(4,1),
  humidity_pct NUMERIC(4,1),
  pressure_hpa NUMERIC(6,1),
  gas_density NUMERIC(6,2),
  pm1 INTEGER,
  pm25 INTEGER,
  pm10 INTEGER,
  wind_speed_ms NUMERIC(4,1),
  battery_v NUMERIC(3,2),
  system_amps NUMERIC(4,3),
  rssi INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (device_id, recorded_at)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_readings_device_time ON readings(device_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_readings_time ON readings(recorded_at DESC);
