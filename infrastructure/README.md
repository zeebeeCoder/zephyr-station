# Zephyr Infrastructure

AWS backend for the Zephyr weather station - API Gateway + Lambda + Supabase PostgreSQL.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ESP32 STATION                                   │
│                                   │                                          │
│                          POST /v1/ingest                                     │
│                          x-api-key: ***                                      │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS API GATEWAY (REST v1)                            │
│                                                                              │
│  ┌─────────────────────┐      ┌─────────────────────┐                       │
│  │   GET /v1/hello     │      │  POST /v1/ingest    │                       │
│  │   (No Auth)         │      │  (API Key Required) │                       │
│  └──────────┬──────────┘      └──────────┬──────────┘                       │
│             │                            │                                   │
│             │    ┌───────────────────────┘                                   │
│             │    │                                                           │
│             ▼    ▼                                                           │
│  ┌─────────────────────────────────────────┐                                │
│  │           API Key Validation            │                                │
│  │         (Usage Plan: 5 req/s)           │                                │
│  └────────────────────┬────────────────────┘                                │
└───────────────────────┼─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS LAMBDA (Node.js 20)                              │
│                              ARM64 / 256MB                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                           handler.mjs                                │    │
│  │                                                                      │    │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │    │
│  │   │   Router     │───▶│    hello     │    │    ingest    │         │    │
│  │   │              │    │   (health)   │    │  (validate)  │         │    │
│  │   └──────────────┘    └──────────────┘    └──────┬───────┘         │    │
│  │                                                   │                  │    │
│  │                              ┌────────────────────┘                  │    │
│  │                              ▼                                       │    │
│  │                    ┌──────────────────┐                             │    │
│  │                    │   Zod Schema     │                             │    │
│  │                    │   Validation     │                             │    │
│  │                    └────────┬─────────┘                             │    │
│  │                             │                                        │    │
│  │                             ▼                                        │    │
│  │                    ┌──────────────────┐                             │    │
│  │                    │   postgres.js    │                             │    │
│  │                    │   (DB Client)    │                             │    │
│  │                    └────────┬─────────┘                             │    │
│  └─────────────────────────────┼────────────────────────────────────────┘    │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SUPABASE (PostgreSQL)                                   │
│                   Session Pooler (IPv4 compatible)                           │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         readings table                               │    │
│  │                                                                      │    │
│  │  id | device_id | recorded_at | temperature_c | humidity_pct | ...  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| API Gateway | REST API v1 | Route requests, API key validation |
| Lambda | Node.js 20, ARM64 | Request handling, validation, DB writes |
| Database | Supabase PostgreSQL | Sensor data storage |
| IaC | Pulumi (JavaScript) | Infrastructure provisioning |

## Endpoints

### GET /v1/hello
Health check endpoint. No authentication required.

**Response:**
```json
{
  "message": "Hello from Zephyr!",
  "service": "zephyr",
  "version": "0.2.0",
  "environment": "dev",
  "timestamp": "2026-01-18T14:17:49.600Z"
}
```

### POST /v1/ingest
Sensor data ingestion. Requires `x-api-key` header.

**Request:**
```json
{
  "device_id": "station-01",
  "timestamp": "2026-01-18T14:30:00Z",
  "readings": {
    "temperature_c": 5.2,
    "humidity_pct": 78,
    "pressure_hpa": 1013,
    "gas_density": 150.5,
    "pm1": 5,
    "pm25": 12,
    "pm10": 18,
    "wind_speed_ms": 2.3
  },
  "meta": {
    "battery_v": 3.92,
    "system_amps": 0.12,
    "rssi": -65
  }
}
```

**Response (success):**
```json
{
  "status": "ok",
  "device_id": "station-01",
  "timestamp": "2026-01-18T14:30:00Z"
}
```

**Response (validation error):**
```json
{
  "error": {
    "message": "Validation failed",
    "errors": [
      { "path": "readings.temperature_c", "message": "Required" }
    ]
  }
}
```

## Schema

### Required Fields
| Field | Type | Range | Description |
|-------|------|-------|-------------|
| device_id | string | 1-64 chars | Station identifier |
| timestamp | string | ISO 8601 | Reading timestamp |
| readings.temperature_c | number | -50 to 60 | Temperature °C |
| readings.humidity_pct | number | 0 to 100 | Relative humidity % |
| readings.pressure_hpa | number | 800 to 1200 | Atmospheric pressure |
| readings.pm25 | integer | 0 to 1000 | PM2.5 µg/m³ |
| readings.pm10 | integer | 0 to 1000 | PM10 µg/m³ |
| meta.battery_v | number | 2.5 to 4.5 | Battery voltage |
| meta.rssi | integer | -120 to 0 | LoRa signal dBm |

### Optional Fields
| Field | Type | Range | Description |
|-------|------|-------|-------------|
| readings.gas_density | number | 0 to 1000 | Gas sensor reading |
| readings.pm1 | integer | 0 to 1000 | PM1.0 µg/m³ |
| readings.wind_speed_ms | number | 0 to 100 | Wind speed m/s |
| meta.system_amps | number | 0 to 5 | Current draw |

## Project Structure

```
infrastructure/
├── index.mjs              # Pulumi stack definition
├── package.json           # Dependencies
├── Pulumi.yaml            # Project config
├── Pulumi.dev.yaml        # Stack config (secrets)
├── src/
│   ├── handler.mjs        # Lambda entry point (router)
│   ├── routes/
│   │   ├── hello.mjs      # Health check handler
│   │   └── ingest.mjs     # Ingest handler
│   └── lib/
│       ├── index.mjs      # Barrel exports
│       ├── config.mjs     # Configuration
│       ├── db.mjs         # Database client
│       ├── logger.mjs     # Structured logging
│       ├── response.mjs   # HTTP response helpers
│       └── schema.mjs     # Zod validation schemas
└── dist/
    └── handler.js         # Bundled output (esbuild)
```

## Deployment

### Prerequisites
- AWS CLI configured with `zephyr` profile
- Pulumi CLI installed
- Node.js 20+
- Supabase project with schema deployed

### Deploy
```bash
cd infrastructure

# Install dependencies
npm install

# Set database URL (one time)
PULUMI_CONFIG_PASSPHRASE="" pulumi config set --secret databaseUrl 'postgresql://...'

# Build and deploy
npm run up
```

### Useful Commands
```bash
npm run build      # Bundle Lambda with esbuild
npm run preview    # Preview changes
npm run up         # Build + deploy
npm run destroy    # Tear down stack
npm run logs       # Stream CloudWatch logs
```

### Get API Key
```bash
PULUMI_CONFIG_PASSPHRASE="" pulumi stack output apiKeyValue --show-secrets
```

## Rate Limiting

| Setting | Value |
|---------|-------|
| Burst limit | 10 requests |
| Rate limit | 5 requests/second |
| Daily quota | 10,000 requests |

## Cost Estimate

| Resource | Free Tier | Monthly Cost |
|----------|-----------|--------------|
| API Gateway (REST) | 1M requests | ~$0.00 |
| Lambda | 1M requests, 400K GB-s | ~$0.00 |
| Supabase | 500MB storage | ~$0.00 |
| **Total** | | **~$0.00** |

At 10,000 requests/month (1 reading every 5 min), well within free tier.

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | Supabase connection string (Pulumi secret) |
| ENVIRONMENT | `dev` or `prod` |

## Security

- API key required for `/ingest` endpoint
- Database credentials stored as Pulumi secrets
- Supabase Session Pooler for IPv4 compatibility
- Rate limiting prevents abuse
