-- The legacy gas_density field stores raw BME680 gas resistance in kΩ.
-- The station radio frame carries the value as uint16_t, so NUMERIC(7,2)
-- preserves the full 0..65535 kΩ wire range.
ALTER TABLE readings
  ALTER COLUMN gas_density TYPE NUMERIC(7,2);
