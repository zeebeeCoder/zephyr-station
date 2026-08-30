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
| DNS | Cloudflare | One external-zone Zephyr API A record |
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
├── cloudflare-dns.mjs     # One DNS-only Zephyr API A record
├── package.json           # Dependencies
├── Pulumi.yaml            # Project config
├── Pulumi.dev.yaml        # Stack config (secrets)
├── test/
│   └── cloudflare-dns.test.mjs
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

# Install the exact locked dependencies
npm ci

# Set database URL (one time)
PULUMI_CONFIG_PASSPHRASE="" pulumi config set --secret databaseUrl 'postgresql://...'

# Review the complete shared-stack preview before any apply
npm run preview
```

This Pulumi stack owns both legacy AWS resources and the Zephyr Cloudflare DNS record. Read the [Cloudflare API DNS runbook](#cloudflare-api-dns-runbook) before either applying or destroying stack resources.

### Useful Commands
```bash
npm run build      # Bundle Lambda with esbuild
npm run preview    # Preview every AWS and Cloudflare change
npm run up         # Apply every reviewed AWS and Cloudflare diff; never DNS alone
npm run destroy    # Destroy all stack-owned AWS resources and the Zephyr DNS record
npm run logs       # Stream CloudWatch logs
```

`npm run up` requires review of the complete shared-stack preview. `npm run destroy` is not a DNS rollback: it requires explicit retirement approval because it destroys all stack-owned legacy AWS resources and the Zephyr DNS record. Use the runbook's reviewed record change for DNS rollback instead.

## Cloudflare API DNS runbook

### Ownership boundary

The Cloudflare zone is external and is **not** a Pulumi-managed resource. This stack declares exactly one `cloudflare:index/dnsRecord:DnsRecord` named `zephyr-api-a`. A record resource manages only the Cloudflare record ID stored in Pulumi state; it is not an authoritative list of zone records. The root website, mail records, frontend records, and every other unrelated zone record remain unmanaged and must not appear in the preview.

The initial resource is deliberately limited to:

- one `A` record for the selected Zephyr backend hostname;
- the selected static public origin IPv4;
- `proxied: false` (DNS-only);
- a 300-second TTL;
- no `AAAA`, zone resource, zone-wide TLS setting, Worker, Page, Rule, or frontend record.

The exact API hostname and static WAN mapping have not been selected/configured yet. Do not invent them: the required config intentionally prevents a preview until the owner supplies both.

### Authentication and configuration

Use the existing token through the environment only. Never set it as Pulumi configuration, export it as a stack output, or commit it:

```bash
cd infrastructure
export CLOUDFLARE_API_TOKEN="$CF_TOKEN"
```

Map the non-secret zone ID and the two owner-selected inputs to these exact Pulumi keys:

```bash
pulumi config set cloudflareZoneId "$CF_DOMAIN_ZONE_ID"
pulumi config set apiHostname '<selected-api-hostname>'
pulumi config set originIpv4 '<selected-static-public-ipv4>'
```

`CF_ACCOUNT_ID` is retained for possible future account-scoped resources. If that scope is approved later, its Pulumi mapping will be `cloudflareAccountId`. The current DNS module neither reads nor requires that key because a zone DNS record needs only `cloudflareZoneId`.

### Discover and import before ownership

Before previewing a real record, inventory the **exact hostname and A-record type** in the Cloudflare dashboard or another approved read-only inventory path. Do not infer absence from this repository.

- If no exact A record exists, continue to preview a create.
- If it exists, obtain its Cloudflare record ID and import it before Pulumi assumes ownership.
- If multiple/conflicting A or CNAME records exist at that hostname, stop for review; do not import, replace, or duplicate anything.

Import command shape (identifiers intentionally represented by variables):

```bash
export CLOUDFLARE_API_TOKEN="$CF_TOKEN"
pulumi import cloudflare:index/dnsRecord:DnsRecord zephyr-api-a \
  "${CF_DOMAIN_ZONE_ID}/${CF_DNS_RECORD_ID}"
```

Import is a live state operation and requires separate approval. After import, run a refresh/preview and verify that Pulumi proposes no replacement or content change unless that exact change was approved.

### Validate and preview

```bash
npm ci
npm run check
npm test
npm run build
pulumi preview --diff
```

Review the complete preview. It is safe to proceed only when all of the following are true:

1. The Cloudflare diff contains exactly the intended `zephyr-api-a` record and no zone or unrelated record resources.
2. The record is type `A`, DNS-only, TTL 300, and points to the approved IPv4; there is no `AAAA` record.
3. A pre-existing exact record was imported and is not proposed for replacement or duplicate creation.
4. There are no deletes or replacements beyond the explicitly reviewed record change.
5. **There is no AWS diff.** This stack still declares the legacy AWS API. Any AWS create, update, replace, or delete blocks the DNS apply, even if caused by unrelated drift.
6. No token or other credential appears in preview text or outputs.

`pulumi up` is intentionally omitted from this workflow. Applying requires a separately reviewed preview and explicit owner approval. DNS apply does not authorize UDM changes, Kamal deployment, TLS enablement, or consumer cutover.

### Rollback

Keep AWS/Supabase and existing consumer URLs intact during DNS rollout. Record the prior target before any approved change.

- For an imported record, restore its prior target through code/config, review a clean preview, and apply only with approval.
- For a newly created record, remove the single declaration through a reviewed code change and apply only with approval.
- Never use rollback to mutate the zone, root website, or unrelated records.
- Re-check public and split-DNS resolution after the 300-second TTL window; revert consumer endpoints separately if they were changed in a later task.

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
| CLOUDFLARE_API_TOKEN | Cloudflare provider authentication; map locally from `CF_TOKEN`, never Pulumi config |

## Security

- API key required for `/ingest` endpoint
- Database credentials stored as Pulumi secrets
- Supabase Session Pooler for IPv4 compatibility
- Rate limiting prevents abuse
