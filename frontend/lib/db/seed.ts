import { DuckDbClient } from './client';
import { readFileSync } from 'fs';
import { join } from 'path';

// ============================================================================
// Types
// ============================================================================

interface SeedConfig {
  devices: DeviceConfig[];
  range: { days: number };
  interval: '1m' | '5m' | '15m';
  patterns: {
    temperature: 'diurnal' | 'flat';
    humidity: 'inverse-temp' | 'flat';
    pm25: 'urban' | 'rural' | 'flat';
    gaps: { probability: number };
  };
}

interface DeviceConfig {
  id: string;
  name: string;
  location: string;
}

interface Reading {
  device_id: string;
  recorded_at: Date;
  temperature_c: number;
  humidity_pct: number;
  pressure_hpa: number;
  pm25: number;
  pm10: number;
  wind_speed_ms: number;
  wind_dir_deg: number;
  battery_v: number;
  rssi: number;
}

// ============================================================================
// Pattern Generators
// ============================================================================

/**
 * Generate diurnal temperature curve
 * Min around 4am (~5°C), Max around 2pm (~20°C) in winter
 */
export function generateDiurnalTemperature(hour: number, baseTemp = 12): number {
  // Cosine wave shifted to have min at 4am, max at 2pm (14:00)
  // Formula: baseTemp + amplitude * cos((hour - peakHour) * PI / 12)
  const amplitude = 7; // +/- 7 degrees from base
  const peakHour = 14; // 2pm
  const radians = ((hour - peakHour) * Math.PI) / 12;
  const temp = baseTemp + amplitude * Math.cos(radians);

  // Add small random variation (+/- 0.5°C)
  return Math.round((temp + (Math.random() - 0.5)) * 10) / 10;
}

/**
 * Generate humidity inversely correlated with temperature
 * Higher humidity at night, lower during day
 */
export function generateInverseHumidity(temperature: number): number {
  // Base humidity 70%, decreases as temp increases
  const baseHumidity = 70;
  const tempEffect = (temperature - 12) * 2; // 2% decrease per degree above 12
  const humidity = baseHumidity - tempEffect + (Math.random() - 0.5) * 5;
  return Math.round(Math.max(30, Math.min(95, humidity)) * 10) / 10;
}

/**
 * Generate PM2.5 with urban pattern (rush hour spikes)
 * Morning rush: 7-9am, Evening rush: 5-7pm
 */
export function generateUrbanPM25(hour: number, basePM = 15): number {
  let pm = basePM;

  // Morning rush hour spike (7-9am)
  if (hour >= 7 && hour <= 9) {
    pm += 20 + Math.random() * 15;
  }
  // Evening rush hour spike (5-7pm)
  else if (hour >= 17 && hour <= 19) {
    pm += 25 + Math.random() * 20;
  }
  // Random cooking spikes (6-8pm)
  else if (hour >= 18 && hour <= 20 && Math.random() < 0.3) {
    pm += 30 + Math.random() * 25;
  }
  // Normal variation
  else {
    pm += (Math.random() - 0.5) * 10;
  }

  return Math.round(Math.max(5, pm));
}

/**
 * Generate PM10 based on PM2.5 (typically 1.5-2x PM2.5)
 */
export function generatePM10(pm25: number): number {
  const ratio = 1.5 + Math.random() * 0.5;
  return Math.round(pm25 * ratio);
}

/**
 * Generate atmospheric pressure (typically 1000-1030 hPa)
 */
export function generatePressure(prevPressure?: number): number {
  const base = prevPressure || 1013;
  // Slow drift with small random walk
  const drift = (Math.random() - 0.5) * 2;
  return Math.round(Math.max(990, Math.min(1040, base + drift)) * 10) / 10;
}

/**
 * Generate wind speed (0-15 m/s typical)
 */
export function generateWindSpeed(): number {
  // Log-normal distribution for wind (most readings are low)
  const u = Math.random();
  const speed = Math.exp(u * 2) - 1;
  return Math.round(Math.min(15, Math.max(0, speed)) * 10) / 10;
}

/**
 * Generate wind direction (0-359 degrees)
 */
export function generateWindDirection(prevDir?: number): number {
  // Slow directional changes
  const base = prevDir ?? Math.floor(Math.random() * 360);
  const change = (Math.random() - 0.5) * 30;
  const result = Math.round(base + change + 360) % 360;
  return result;
}

/**
 * Generate battery voltage (3.0V depleted, 4.2V full)
 * Gradual drain with solar charging during day
 */
export function generateBatteryVoltage(hour: number, dayOfWeek: number): number {
  // Base voltage decreases over time
  const baseVoltage = 4.0 - (dayOfWeek * 0.05);

  // Solar charging effect during daylight (8am-6pm)
  let voltage = baseVoltage;
  if (hour >= 8 && hour <= 18) {
    voltage += 0.1 + Math.random() * 0.1;
  } else {
    voltage -= 0.02;
  }

  return Math.round(Math.max(3.2, Math.min(4.2, voltage)) * 100) / 100;
}

/**
 * Generate RSSI (signal strength, typically -30 to -90 dBm)
 */
export function generateRSSI(): number {
  // Most readings around -60 to -70
  return Math.round(-60 - Math.random() * 20);
}

// ============================================================================
// Seed Configuration
// ============================================================================

const DEFAULT_CONFIG: SeedConfig = {
  devices: [
    { id: 'station-01', name: 'Garden Station', location: 'Backyard, south fence' },
  ],
  range: { days: 7 },
  interval: '5m',
  patterns: {
    temperature: 'diurnal',
    humidity: 'inverse-temp',
    pm25: 'urban',
    gaps: { probability: 0.02 }, // 2% chance of gap
  },
};

function getIntervalMs(interval: string): number {
  switch (interval) {
    case '1m': return 60 * 1000;
    case '5m': return 5 * 60 * 1000;
    case '15m': return 15 * 60 * 1000;
    default: return 5 * 60 * 1000;
  }
}

// ============================================================================
// Reading Generation
// ============================================================================

function generateReading(
  device: DeviceConfig,
  time: Date,
  dayOfWeek: number,
  patterns: SeedConfig['patterns'],
  prevPressure?: number,
  prevWindDir?: number
): { reading: Reading; pressure: number; windDir: number } {
  const hour = time.getHours();

  const temperature = patterns.temperature === 'diurnal'
    ? generateDiurnalTemperature(hour)
    : 15 + (Math.random() - 0.5) * 2;

  const humidity = patterns.humidity === 'inverse-temp'
    ? generateInverseHumidity(temperature)
    : 60 + (Math.random() - 0.5) * 10;

  const pm25 = patterns.pm25 === 'urban'
    ? generateUrbanPM25(hour)
    : 10 + Math.random() * 5;

  const pressure = generatePressure(prevPressure);
  const windDir = generateWindDirection(prevWindDir);

  return {
    reading: {
      device_id: device.id,
      recorded_at: new Date(time),
      temperature_c: temperature,
      humidity_pct: humidity,
      pressure_hpa: pressure,
      pm25: pm25,
      pm10: generatePM10(pm25),
      wind_speed_ms: generateWindSpeed(),
      wind_dir_deg: windDir,
      battery_v: generateBatteryVoltage(hour, dayOfWeek),
      rssi: generateRSSI(),
    },
    pressure,
    windDir,
  };
}

export function generateReadings(config: SeedConfig = DEFAULT_CONFIG): Reading[] {
  const readings: Reading[] = [];
  const intervalMs = getIntervalMs(config.interval);
  const endTime = new Date();
  const startTime = new Date(endTime.getTime() - config.range.days * 24 * 60 * 60 * 1000);

  let currentTime = new Date(startTime);
  let prevPressure: number | undefined;
  let prevWindDir: number | undefined;

  while (currentTime <= endTime) {
    if (Math.random() < config.patterns.gaps.probability) {
      const skipCount = 1 + Math.floor(Math.random() * 3);
      currentTime = new Date(currentTime.getTime() + intervalMs * skipCount);
      continue;
    }

    const dayOfWeek = Math.floor((currentTime.getTime() - startTime.getTime()) / (24 * 60 * 60 * 1000));

    for (const device of config.devices) {
      const result = generateReading(device, currentTime, dayOfWeek, config.patterns, prevPressure, prevWindDir);
      readings.push(result.reading);
      prevPressure = result.pressure;
      prevWindDir = result.windDir;
    }

    currentTime = new Date(currentTime.getTime() + intervalMs);
  }

  return readings;
}

// ============================================================================
// Database Operations (extracted from seed)
// ============================================================================

async function initializeSchema(client: DuckDbClient): Promise<void> {
  console.log('📋 Initializing schema...');
  const schemaPath = join(__dirname, 'schema.sql');
  const schema = readFileSync(schemaPath, 'utf-8');
  const statements = schema.split(';').map(s => s.trim()).filter(s => s.length > 0);

  for (const stmt of statements) {
    await client.query(stmt);
  }
}

async function clearData(client: DuckDbClient): Promise<void> {
  console.log('🗑️  Clearing existing data...');
  await client.query('DELETE FROM readings');
  await client.query('DELETE FROM devices');
}

async function insertDevices(client: DuckDbClient, devices: DeviceConfig[]): Promise<void> {
  console.log('📱 Inserting devices...');
  for (const device of devices) {
    // Use parameterized query to prevent SQL injection
    await client.query(
      `INSERT INTO devices (id, name, location, installed_at, is_active) VALUES (?, ?, ?, ?, ?)`,
      [device.id, device.name, device.location, new Date().toISOString(), true]
    );
  }
}

async function insertReadingsBatch(
  client: DuckDbClient,
  readings: Reading[],
  batchSize = 500
): Promise<void> {
  console.log('💾 Inserting readings (batch)...');
  let inserted = 0;

  for (let i = 0; i < readings.length; i += batchSize) {
    const batch = readings.slice(i, i + batchSize);

    // Build parameterized batch insert
    const placeholders = batch.map((_, idx) => `(${i + idx + 1}, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).join(', ');
    const params = batch.flatMap(r => [
      r.device_id,
      r.recorded_at.toISOString(),
      r.temperature_c,
      r.humidity_pct,
      r.pressure_hpa,
      r.pm25,
      r.pm10,
      r.wind_speed_ms,
      r.wind_dir_deg,
      r.battery_v,
      r.rssi,
    ]);

    await client.query(
      `INSERT INTO readings (id, device_id, recorded_at, temperature_c, humidity_pct, pressure_hpa, pm25, pm10, wind_speed_ms, wind_dir_deg, battery_v, rssi) VALUES ${placeholders}`,
      params
    );

    inserted += batch.length;
    process.stdout.write(`\r   Inserted ${inserted}/${readings.length} readings`);
  }

  console.log('');
}

async function showSample(client: DuckDbClient): Promise<void> {
  const sample = await client.query<Reading>(
    `SELECT * FROM readings ORDER BY recorded_at DESC LIMIT 3`
  );
  console.log('\n📈 Latest readings:');
  console.table(sample);
}

// ============================================================================
// Main Seed Function (orchestration only)
// ============================================================================

export async function seed(config: SeedConfig = DEFAULT_CONFIG): Promise<void> {
  console.log('🌱 Starting seed...');
  console.log(`   Config: ${config.range.days} days, ${config.interval} interval`);

  const client = new DuckDbClient(process.env.DATABASE_URL || 'local.db');

  try {
    await initializeSchema(client);
    await clearData(client);
    await insertDevices(client, config.devices);

    console.log('📊 Generating readings...');
    const readings = generateReadings(config);
    console.log(`   Generated ${readings.length} readings`);

    await insertReadingsBatch(client, readings);
    await showSample(client);

    console.log('✅ Seed complete!');
  } finally {
    await client.close();
  }
}

// Run if called directly
if (require.main === module) {
  seed().catch(console.error);
}
