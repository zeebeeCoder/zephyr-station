-- Zephyr Weather Station Schema
-- Compatible with both DuckDB (dev) and PostgreSQL (prod)

CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  location TEXT,
  installed_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY,
  device_id TEXT NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL,
  temperature_c DECIMAL(4,1),
  humidity_pct DECIMAL(4,1),
  pressure_hpa DECIMAL(6,1),
  gas_density DECIMAL(6,2),
  pm1 INTEGER,
  pm25 INTEGER,
  pm10 INTEGER,
  wind_speed_ms DECIMAL(4,1),
  battery_v DECIMAL(3,2),
  system_amps DECIMAL(4,3),
  rssi INTEGER,
  FOREIGN KEY (device_id) REFERENCES devices(id)
);

CREATE INDEX IF NOT EXISTS idx_readings_time ON readings(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_readings_device ON readings(device_id);
