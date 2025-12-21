# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Zephyr** is a hyperlocal weather station with an AI chatbot interface. The system collects environmental data from ESP32-based sensors and makes it queryable via natural language.

**Data flow**: ESP32 sensors → LoRa → Master node → AWS Lambda → Supabase (PostgreSQL) → Next.js + Vercel AI SDK

## Architecture

### Four-Layer System

1. **Outdoor Station**: ESP32 + LoRa with sensors. Solar/battery powered. Buffers readings when no ACK.
2. **Master Node**: ESP32 "dumb pipe" (~50 lines). LoRa → HTTPS → ACK. Mains powered, stateless.
3. **AWS Backend**: API Gateway + Lambda + Pulumi. Generic Postgres interface.
4. **Frontend**: Next.js on Vercel. Vercel AI SDK with SQL tool calls via `postgres.js`.

### Key Design Decisions

- **Single database**: Supabase PostgreSQL (no InfluxDB/S3/DuckDB)
- **Sender-side resilience**: Outdoor station buffers, gateway is stateless
- **Generic Postgres**: Standard SQL everywhere, no proprietary SDKs
- **Cross-cloud**: Vercel frontend ↔ AWS backend

### Constraints

- Monthly cost: <$5
- Data latency: <10s from reading to queryable
- Offline resilience: Station buffers when connectivity lost

---

## Complexity Management Framework

### Types of Complexity

- **Essential Complexity**: Inherent to the business domain; manage through clear abstractions.
- **Accidental Complexity**: Resulting from poor design or inappropriate tools; eliminate by simplifying.
- **Incidental Complexity**: Infrastructure overhead; minimize through consolidation of tools and processes.

### Fundamental Principle

**Proper modularity and simplification enable parallel development. Accidental complexity creates unnecessary coordination overhead.**

## Decision Framework

### Pre-Development Complexity Assessment

When planning, solutioning or breakingin down possible paths, ask:

1. "Is this complexity inherent to the business problem or am I introducing it?"
2. "What's the simplest solution to handle essential complexity?"
3. "Can one team build this independently?"
4. "Which interfaces must remain stable for parallel work?"

Validate using Farley's criteria:

- **Modularity**: Can it be divided into independent modules?
- **Cohesion**: Are related elements grouped logically?
- **Coupling**: Are dependencies minimal and explicit?
- **Abstraction**: Does it hide complexity effectively or introduce unnecessary layers?

### Red Flags for Complexity

Simplify immediately if you detect:

- More than three abstraction levels for a single concept.
- Patterns used without clear business justification.
- Dependencies unrelated to core functionality.
- Multiple teams coordinating on a single feature.
- Frequent interface changes requiring cross-team coordination.
- Extensive documentation needed to understand code.

Avoid accidental complexity statements like:

❌ "We should use [pattern] because it's best practice."
❌ "This needs to be enterprise-grade from day one."
❌ "Let's make it scalable for every possible use case."

Instead, prefer:

✓ "What's the simplest solution that works?"
✓ "Can we start with a minimal viable approach?"
✓ "What would break if we simplified this?"

---

## References

- [PRD & Technical Design](docs/prd-tech-design.md) - Full project specification, architecture, and phased roadmap
