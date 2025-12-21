---
title: Zephyr - PRD & Technical Design
codename: Zephyr
created: 2025-12-20
status: draft
tags: [project, iot, esp32, weather, mikolaj, zephyr]
license: MIT
repo: zephyr-station
---

# Zephyr: Hyperlocal Weather Intelligence

> Hyperlocal weather station with AI chatbot interface. ESP32 + LoRa → AWS → Supabase → Next.js.

**Codename**: Zephyr (Greek god of the west wind)

---

## Part 1: The WHY

### Problem Statement

Existing weather apps and services fail our household in three ways:

1. **Location mismatch**: Data comes from weather stations kilometers away, missing our microclimate (garden frost, local wind patterns, street-level air quality)
2. **Missing metrics**: Can't get hyperlocal particulate matter (PM2.5/PM10), real wind at our location, or correlated multi-sensor insights
3. **Stale data**: Hourly averages and forecasts, not real-time readings when conditions are changing

### Vision

A self-built weather station that:
- Provides **hyperlocal, real-time** environmental data from our property
- Enables **conversational queries** ("Should I open the windows?" "How does air quality compare to yesterday?")
- Serves as a **full-stack learning project** for Mikolaj covering embedded systems, cloud infrastructure, and AI

### Success Criteria (6 months)

| Metric | Target |
|--------|--------|
| **System reliability** | Station sends data reliably, viewable 24/7, family actively uses it |
| **Mikolaj's growth** | Understands full stack: firmware → cloud → frontend; can explain architecture |
| **Portfolio artifact** | GitHub repo demonstrates real engineering, deployable demo |

### Constraints

| Constraint | Limit |
|------------|-------|
| **Monthly cost** | < $5/month (free tiers + minimal paid) |
| **Offline resilience** | System functions when internet is down (local fallback) |
| **Maintainability** | Simple enough Mikolaj can maintain solo eventually |

---

## Part 2: The WHAT

### Users & Use Cases

**Primary users**: Family household members

| Use Case | Example Query | Priority |
|----------|---------------|----------|
| Current conditions | "What's the temperature?" "Is air quality safe?" | MVP |
| Comparisons | "Is it warmer than yesterday?" "Wind trend this week?" | MVP |
| Recommendations | "Should I open windows?" "Good weather for a run?" | MVP |
| Alerts/anomalies | "When did PM2.5 spike?" "Any unusual readings?" | MVP |
| Historical analysis | "Compare this week to last year" "Seasonal patterns" | Post-MVP |
| External comparison | "How does our reading compare to city average?" | Post-MVP |

### Functional Requirements

#### FR-1: Data Collection
- Collect readings from sensors: temperature, humidity, air quality (PM), wind speed, wind direction
- Transmission frequency: configurable (default 5 min), future adaptive mode
- Battery level monitoring and reporting from outdoor station
- Local buffering when connectivity lost

#### FR-2: Data Storage
- Real-time data accessible for queries (last 30 days minimum)
- Historical data archived for long-term analysis (years)
- Query-able via SQL-like interface

#### FR-3: Conversational Interface
- Natural language queries about weather data
- Context-aware responses (knows current conditions without asking)
- Progressive output: text/markdown → pre-built widgets → dynamic visualizations

#### FR-4: System Observability
- Telemetry on all system components (station health, data flow, cloud services)
- Battery level alerts
- Data gap detection

### Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Latency** | < 10s from reading to queryable |
| **Availability** | 99% uptime for cloud components |
| **Data retention** | Unlimited (PostgreSQL handles years of weather data easily) |
| **Security** | API keys secured, no public write access |

---

## Part 3: The HOW

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTDOOR STATION                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Temp/Humid  │  │ Air Quality │  │ Wind Speed  │  │ Wind Dir    │         │
│  │ (BME280)    │  │ (PMS5003)   │  │ (Anemometer)│  │ (Vane)      │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┴────────────────┴────────────────┘                 │
│                                    │                                         │
│                          ┌─────────▼─────────┐                              │
│                          │      ESP32        │◄──── Solar + Battery         │
│                          │ (DeepSleep+Buffer)│      Buffering on no ACK     │
│                          └─────────┬─────────┘                              │
│                                    │ LoRa (+ ACK)                           │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ 20-50m
┌────────────────────────────────────┼────────────────────────────────────────┐
│                         MASTER NODE (Dumb Pipe)                              │
│                          ┌─────────▼─────────┐                              │
│                          │      ESP32        │◄──── Mains Power             │
│                          │  Listen → Forward │      No buffering            │
│                          └─────────┬─────────┘                              │
│                                    │ HTTPS (fire & forget)                  │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                              AWS BACKEND                                     │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐      │
│  │ API Gateway  │───▶│    Lambda    │───▶│  PostgreSQL (Supabase)   │      │
│  │  /ingest     │    │  (Ingest)    │    │  - readings table        │      │
│  └──────────────┘    └──────────────┘    │  - SQL queries           │      │
│                                          │  - Unlimited retention   │      │
│  ┌──────────────────────────────────┐    └──────────────────────────┘      │
│  │  INFRASTRUCTURE (Pulumi)         │                                       │
│  │  API Gateway │ Lambda │ IAM      │                                       │
│  └──────────────────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                         VERCEL (Frontend)                                    │
│                                                                             │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐            │
│  │   Next.js App  │───▶│  Vercel AI SDK │───▶│   LLM (Claude/ │            │
│  │   (Chatbot UI) │    │  (Tool Calls)  │    │   GPT/etc)     │            │
│  └────────────────┘    └───────┬────────┘    └────────────────┘            │
│                                │                                            │
│                        ┌───────▼────────┐                                  │
│                        │  SQL Tools     │──────▶ Supabase API              │
│                        │  (SELECT *)    │                                  │
│                        └────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key simplifications**:
- **Single database**: PostgreSQL (Supabase) replaces InfluxDB + S3 + DuckDB
- **Dumb gateway**: Master node just forwards, no buffering logic
- **Sender-side resilience**: Outdoor station buffers on no LoRa ACK
- **Cross-cloud**: Vercel frontend ↔ AWS backend (Mikolaj learns integration)

### Component Breakdown

#### C1: Outdoor Station (Sender)

| Aspect | Decision |
|--------|----------|
| **MCU** | ESP32 (with LoRa module, e.g., TTGO LoRa32) |
| **Power** | Solar panel + LiPo battery, deep sleep between readings |
| **Sensors** | BME280 (temp/humidity/pressure), PMS5003 (PM2.5/PM10), anemometer + wind vane |
| **Communication** | LoRa to master node (low power, 20-50m range) |
| **Firmware** | Arduino C++ |
| **Resilience** | Sender-side buffering: if no LoRa ACK, store in RTC memory, batch-send next cycle |

**Key firmware behaviors**:
- Wake every N minutes (configurable)
- Read all sensors
- Transmit via LoRa, wait for ACK
- **If ACK received**: clear buffer, deep sleep
- **If no ACK**: store reading in RTC memory (up to ~8 readings)
- Next wake: send buffered readings first, then current
- Report battery voltage

#### C2: Master Node (Dumb Pipe)

| Aspect | Decision |
|--------|----------|
| **MCU** | ESP32 (with LoRa + WiFi) |
| **Power** | Mains (USB adapter) |
| **Role** | Receive LoRa → immediately forward to cloud → send ACK |
| **Buffering** | None (resilience lives in sender) |
| **Complexity** | Minimal - just a passthrough |

**Key firmware behaviors** (simple loop):
```
loop:
  1. Listen for LoRa packet
  2. Parse payload
  3. POST to cloud endpoint (fire & forget)
  4. Send LoRa ACK back to station
  5. Repeat
```

This keeps master node firmware trivially simple (~50 lines).

#### C3: Cloud Ingestion (AWS Lambda)

| Aspect | Decision |
|--------|----------|
| **Trigger** | API Gateway (POST /ingest) |
| **Auth** | API key in header (simple), future: device certificates |
| **Processing** | Validate payload, INSERT into PostgreSQL |
| **Language** | Python or TypeScript |
| **Database** | Generic Postgres interface (connection string via env var) |

**Design principle**: Lambda talks to "Postgres", not "Supabase". The same code works with Supabase, RDS, or a VPS - just change the connection string.

```python
# Pseudocode - generic Postgres insert
def handler(event):
    payload = validate(event['body'])
    conn = psycopg2.connect(os.environ['DATABASE_URL'])  # Could be Supabase, RDS, or VPS
    conn.execute("INSERT INTO readings (...) VALUES (...)", payload)
```

**Payload schema** (example):
```json
{
  "device_id": "station-01",
  "timestamp": "2025-12-20T14:30:00Z",
  "readings": {
    "temperature_c": 5.2,
    "humidity_pct": 78,
    "pressure_hpa": 1013,
    "pm25": 12,
    "pm10": 18,
    "wind_speed_ms": 3.4,
    "wind_dir_deg": 225
  },
  "meta": {
    "battery_v": 3.92,
    "rssi": -65
  }
}
```

#### C4: Data Storage (PostgreSQL / Supabase)

**Strategy**: "The Springboard" - use managed Postgres to remove infrastructure from the critical path.

| Aspect | Decision |
|--------|----------|
| **Provider** | Supabase (free tier: 500MB, 2 projects) |
| **Query language** | SQL (transferable career skill for Mikolaj) |
| **Retention** | Unlimited within free tier |
| **Access** | Postgres driver (generic) or Supabase JS client |
| **Security** | RLS enabled: public read, service role write |

**Data volume justification**:
- 1 reading every 5 min = 105,000 rows/year
- Row size: ~100 bytes
- **1 year = ~10 MB**
- Free tier (500MB) = **~40 years of data**

**Schema**:
```sql
CREATE TABLE readings (
  id SERIAL PRIMARY KEY,
  device_id TEXT NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL,
  temperature_c NUMERIC(4,1),
  humidity_pct NUMERIC(4,1),
  pressure_hpa NUMERIC(6,1),
  pm25 INTEGER,
  pm10 INTEGER,
  wind_speed_ms NUMERIC(4,1),
  wind_dir_deg INTEGER,
  battery_v NUMERIC(3,2),
  rssi INTEGER
);

CREATE INDEX idx_readings_time ON readings(recorded_at DESC);

-- Row Level Security
ALTER TABLE readings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read" ON readings FOR SELECT USING (true);
CREATE POLICY "Service write" ON readings FOR INSERT WITH CHECK (true);
```

**Why Supabase (not S3/Firehose or VPS)**:
- **vs S3/Firehose**: Overkill. Requires Glue schema, IAM roles, 60-300s latency. Kills momentum.
- **vs VPS**: Great long-term, but requires Linux knowledge upfront. Phase 2 option.
- **Supabase**: Real-time (<1s), zero maintenance, click-and-go.

**Exit strategy (two-way door)**:
> "If we outgrow it or want to self-host, we pg_dump to a $3.50/month VPS in 10 minutes. It's standard Postgres - no lock-in."

| Phase | Data Layer |
|-------|------------|
| Phase 1 (months 1-6) | Supabase (free) |
| Phase 2 (month 6+) | Optional: VPS + Docker if Mikolaj wants to learn Linux |

#### C5: The AI Agent & Client

##### 5.1 The Stack ("The Springboard")

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Framework** | Next.js 14+ (App Router) | Standard React framework; optimized for Vercel |
| **Hosting** | Vercel (Hobby Tier) | Zero config, free SSL/CDN, huge free tier for compute |
| **AI Orchestration** | Vercel AI SDK (Core) | Unified API for streaming and tool calling. Prevents vendor lock-in to specific LLMs |
| **Database** | Supabase (PostgreSQL) | Standard SQL DB. Free tier. Easy migration path to self-hosted later |
| **Driver** | `postgres.js` | Standard, fast SQL driver. No proprietary SDKs |
| **Styling** | Tailwind CSS | Utility-first, fast iteration |

##### 5.2 The Execution Model: "Stateless Node.js Agent"

We avoid "Edge Functions" and "SaaS SDKs" to prevent timeouts and connection limits. The agent runs as a standard **Node.js Serverless Function**.

**The Loop (Request Lifecycle):**

1. **User Input:** User types *"Did it freeze last night?"*

2. **Ingest (Vercel):** Request hits `POST /api/chat`
   - **Runtime:** `Node.js` (Not Edge). Ensures full TCP support for database connections.
   - **Duration:** Function stays alive for the duration of the stream (10-60s depending on plan)

3. **Reasoning (LLM):**
   - Vercel AI SDK forwards context + Tool Definitions to **Claude 3.5 Sonnet**
   - *System Prompt:* Includes "Current Time" so the LLM understands "last night"

4. **Tool Call (The "Body"):**
   - LLM pauses and requests tool: `query_readings({ start: '2025-12-20T22:00', end: '...' })`
   - **Next.js Server** executes the tool code locally
   - **SQL Execution:** Connects to Supabase via **Transaction Pooler (Port 6543)** to prevent connection exhaustion
   - **Result:** Returns raw JSON rows (e.g., `[{ "temp": -1.2, "time": ... }]`) to the LLM

5. **Response (Streaming):**
   - LLM interprets the data: *"Yes, the temperature dropped to -1.2°C at 4:00 AM."*
   - Text is streamed token-by-token to the frontend

##### 5.3 Data Access Strategy

To ensure transferable skills for Mikolaj, we strictly use **Standard SQL** rather than ORMs or SDK wrappers.

- **Connection:** `postgres://user:pass@...pooler.supabase.com:6543/postgres`
- **Security:** Connection string stored in `VERCEL_ENV`
- **Pattern:**

```typescript
// app/api/chat/route.ts
import postgres from 'postgres';

// 1. Singleton SQL connection (Serverless friendly)
const sql = postgres(process.env.DATABASE_URL!);

// 2. Tool Definition
const tools = {
  get_readings: tool({
    description: 'Get weather data for a time range',
    parameters: z.object({ start: z.string(), end: z.string() }),
    execute: async ({ start, end }) => {
      // 3. Raw SQL - Transferable Skill!
      return await sql`
        SELECT * FROM readings
        WHERE recorded_at BETWEEN ${start} AND ${end}
        ORDER BY recorded_at DESC
      `;
    }
  })
};
```

##### 5.4 Architecture Diagram (Sequence)

```
┌──────┐      ┌─────────────────┐      ┌───────────┐      ┌─────────────────┐
│ User │      │ Vercel (Node.js)│      │ Claude API│      │ Supabase :6543  │
└──┬───┘      └────────┬────────┘      └─────┬─────┘      └────────┬────────┘
   │                   │                     │                     │
   │ "Was it cold      │                     │                     │
   │  yesterday?"      │                     │                     │
   │──────────────────>│                     │                     │
   │                   │                     │                     │
   │                   │  Send Conversation  │                     │
   │                   │  + Tool Definitions │                     │
   │                   │────────────────────>│                     │
   │                   │                     │                     │
   │                   │   Request Tool:     │                     │
   │                   │   query_readings()  │                     │
   │                   │<────────────────────│                     │
   │                   │                     │                     │
   │                   │  SELECT min(temp)   │                     │
   │                   │  WHERE date = ...   │                     │
   │                   │─────────────────────────────────────────> │
   │                   │                     │                     │
   │                   │                     │    Returns: -1.2°C  │
   │                   │<───────────────────────────────────────── │
   │                   │                     │                     │
   │                   │  Send Tool Result   │                     │
   │                   │────────────────────>│                     │
   │                   │                     │                     │
   │                   │  Stream Response:   │                     │
   │                   │  "Yes, it dropped   │                     │
   │                   │   to -1.2°C..."     │                     │
   │                   │<────────────────────│                     │
   │                   │                     │                     │
   │  Stream text      │                     │                     │
   │<──────────────────│                     │                     │
   │                   │                     │                     │
```

##### 5.5 Cost & Scale Safety

| Service | Limit | Family Usage | Safety Margin |
|---------|-------|--------------|---------------|
| **Vercel** | 100 GB-Hours free | ~24,000 queries/month capacity | >99% headroom |
| **Supabase** | Transaction Pooler (Supavisor) | Handles chat spikes, prevents "too many clients" | Built-in |
| **Claude** | Pay-per-token | Variable cost | **Budget alert at $5.00** |

##### 5.6 Progressive Output Roadmap

1. **MVP**: Text/markdown responses
2. **V2**: Pre-built chart components (line graph, gauge)
3. **V3**: Dynamic React component generation

##### 5.7 Cross-Cloud Integration (Learning Opportunity)

- Frontend on Vercel calls AWS API Gateway for ingestion endpoint
- Frontend queries Supabase directly for reads (via pooled connection)
- Mikolaj learns: environment variables, CORS, API keys across services

#### C6: Infrastructure as Code (Pulumi)

**AWS Backend** (Pulumi):
| Resource | Pulumi Component |
|----------|------------------|
| API Gateway | `aws.apigateway.RestApi` |
| Lambda | `aws.lambda.Function` |
| IAM | `aws.iam.Role`, `aws.iam.Policy` |
| CloudWatch | `aws.cloudwatch.*` (basic alarms) |

**Vercel Frontend** (Pulumi or manual):
| Resource | Approach |
|----------|----------|
| Vercel Project | `pulumiverse/vercel` provider OR just `vercel` CLI deploy |

**Supabase** (manual setup, not IaC):
- Create project via Supabase dashboard
- Store connection string as environment variable

**Stack structure** (simplified):
```
infrastructure/
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── index.ts
└── components/
    ├── ingestion.ts    # API GW + Lambda
    └── monitoring.ts   # CloudWatch alarms
```

**Note**: Keeping Supabase + Vercel outside Pulumi is pragmatic for MVP. IaC everything later if needed.

### Monorepo Structure

```
zephyr-station/
├── README.md
├── .github/
│   └── workflows/           # CI/CD (optional)
├── firmware/
│   ├── station/             # Outdoor station (Arduino C++)
│   │   ├── station.ino
│   │   └── README.md
│   └── gateway/             # Master node - dumb pipe (~50 lines)
│       ├── gateway.ino
│       └── README.md
├── infrastructure/
│   ├── Pulumi.yaml
│   ├── index.ts
│   └── components/
│       ├── ingestion.ts     # API GW + Lambda
│       └── monitoring.ts    # CloudWatch
├── backend/
│   └── functions/
│       └── ingest/          # Lambda: validate → INSERT into Supabase
├── frontend/
│   ├── package.json
│   ├── app/
│   ├── components/
│   └── lib/
│       └── tools/           # LLM tool definitions (SQL queries)
└── docs/
    └── architecture.md
```

---

## Part 4: Phased Roadmap

### Phase 1: Foundation (MVP)

**Goal**: End-to-end data flow, basic chatbot query works

| Task | Owner | Notes |
|------|-------|-------|
| Set up GitHub repo + branch protection | Zbigniew | Invite Mikolaj as collaborator |
| Create Supabase project + readings table | Zbigniew | Manual setup, store connection string |
| Outdoor station firmware (temp/humidity only) | Mikolaj + CC | Start simple, one sensor, no buffering yet |
| Master node firmware (dumb pipe) | Mikolaj + CC | ~50 lines: listen → forward → ACK |
| Pulumi stack: API GW + Lambda | Zbigniew | Lambda inserts to Supabase |
| Deploy Next.js to Vercel | Zbigniew | Vercel AI SDK scaffold |
| `get_current_readings` tool | Zbigniew | First SQL query via LLM |

**Exit criteria**: Ask "What's the temperature?" → get live answer

**First win for Mikolaj**: See his sensor data appear in the chatbot

### Phase 2: Full Sensor Suite

**Goal**: All sensors operational, richer queries

| Task | Owner |
|------|-------|
| Add air quality sensor (PMS5003) | Mikolaj |
| Add wind sensors (anemometer + vane) | Mikolaj |
| Battery monitoring + reporting | Mikolaj |
| `query_time_range` tool | Zbigniew |
| `compare_periods` tool | Zbigniew |
| Recommendations logic | Zbigniew |

**Exit criteria**: All sensors reporting, can compare "today vs yesterday"

### Phase 3: Resilience & Observability

**Goal**: System survives connectivity issues, self-monitors

| Task | Owner |
|------|-------|
| Sender-side buffering (outdoor station) | Mikolaj |
| LoRa ACK protocol | Mikolaj |
| CloudWatch alarms (Lambda errors, latency) | Zbigniew |
| Battery low alerts (query-based) | Zbigniew |
| Data gap detection (SQL query) | Zbigniew |

**Exit criteria**: Station buffers readings when gateway offline, alerts on issues

### Phase 4: External Data & Comparisons

**Goal**: Compare with external sources, long-term analysis

| Task | Owner |
|------|-------|
| External weather API integration | Mikolaj |
| "Compare to city average" feature | Mikolaj |
| Historical queries (SQL handles years of data) | Zbigniew |
| Seasonal comparison queries | Zbigniew |

**Exit criteria**: "How does our air quality compare to the city?"

### Phase 5: Enhanced Visualization

**Goal**: Rich UI beyond text responses

| Task | Owner |
|------|-------|
| Pre-built chart components (line, gauge) | Mikolaj |
| Widget rendering in chat responses | Zbigniew |
| Basic dashboard view (non-chat) | Mikolaj |
| (Stretch) Dynamic component generation | Zbigniew |

**Exit criteria**: Chatbot returns visual charts, optional dashboard view

---

## Part 5: Open Questions & Decisions

| # | Question | Options | Status |
|---|----------|---------|--------|
| 1 | ~~Database choice~~ | ~~InfluxDB vs Postgres~~ | **DECIDED: Supabase PostgreSQL** |
| 2 | ~~Frontend hosting~~ | ~~Vercel vs Amplify~~ | **DECIDED: Vercel (optimized for Next.js)** |
| 3 | SSH keys for Mikolaj on shared Mac? | Separate macOS user, or SSH config with multiple keys | TBD |
| 4 | Enclosure for outdoor station? | 3D print, buy weatherproof box, DIY | TBD |
| 5 | Solar panel sizing for Polish winter? | Need to calculate power budget | TBD |
| 6 | Adaptive frequency algorithm? | Simple threshold-based vs ML-based | **Defer to Phase 4+** |

---

## Appendix A: Cost Estimate

| Service | Free Tier | Estimated Monthly |
|---------|-----------|-------------------|
| Supabase | 500MB storage, 2 projects | $0 |
| AWS Lambda | 1M requests/month | $0 |
| AWS API Gateway | 1M calls/month | $0 |
| Vercel | 100GB bandwidth, hobby tier | $0 |
| LLM API (Claude/GPT) | Pay per token | ~$1-3 (depending on usage) |
| **Total** | | **~$1-3/month** |

**Simpler stack = fewer moving parts = lower risk of surprise costs**

---

## Appendix B: Reference Links

**Hardware**:
- [ESP32 LoRa guide](https://randomnerdtutorials.com/esp32-lora-rfm95-transceiver-arduino-ide/)
- [PMS5003 sensor datasheet](https://www.aqmd.gov/docs/default-source/aq-spec/resources-page/plantower-pms5003-manual_v2-3.pdf)
- [BME280 guide](https://randomnerdtutorials.com/esp32-bme280-arduino-ide-pressure-temperature-humidity/)

**Cloud/Backend**:
- [Supabase docs](https://supabase.com/docs)
- [Supabase JS client](https://supabase.com/docs/reference/javascript/introduction)
- [Pulumi AWS provider](https://www.pulumi.com/registry/packages/aws/)

**Frontend**:
- [Vercel AI SDK](https://sdk.vercel.ai/docs)
- [Next.js App Router](https://nextjs.org/docs/app)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2025-12-20 | Zbigniew + Claude | Initial draft from discovery interview |
| 2025-12-20 | Zbigniew + Claude | **v2**: Simplified architecture - unified PostgreSQL (Supabase), dumb gateway, hybrid hosting (Vercel + AWS) |
| 2025-12-20 | Zbigniew + Claude | **v2.1**: Added data volume justification (10MB/year), RLS security, exit strategy (VPS migration), generic Lambda design |
| 2025-12-20 | Zbigniew + Claude | **v2.2**: Codename "Zephyr", MIT license, detailed AI Agent spec (Vercel AI SDK, postgres.js, Node.js runtime, connection pooling) |
