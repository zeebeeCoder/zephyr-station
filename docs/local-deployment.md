# Local Deployment Runbook

Staging target: `sagent@192.168.1.50` (LAN, private HTTP, no consumer cutover).

## Prerequisites

- SSH to `sagent@192.168.1.50` verified; Docker on host
- Ports 80/443/3000/5432 free on host
- GitHub CLI authenticated with `repo` **and `write:packages`** scopes
- Ruby/bundler installed locally; run `bundle install`

## Secrets

Kamal resolves declared secrets through `.kamal/secrets`. On a clean checkout this file does not exist.

**Option A: Export in shell (recommended)** — create `.kamal/secrets` from the example, then export variables in your shell and leave the forwarding lines unchanged:

```bash
cp .kamal/secrets.example .kamal/secrets
export KAMAL_REGISTRY_PASSWORD=<ghcr-token>
export POSTGRES_PASSWORD=<strong-password>
export DATABASE_URL=postgres://zephyr:<password>@zephyr-postgres:5432/zephyr
export INGEST_API_KEY=<api-key>
```

The forwarding lines in `.kamal/secrets` (`KAMAL_REGISTRY_PASSWORD=$KAMAL_REGISTRY_PASSWORD`) resolve through the shell environment.

**Option B: Write values directly to `.kamal/secrets`** — copy the example, replace forwarding lines with real values, set mode 600:

```bash
cp .kamal/secrets.example .kamal/secrets
# Edit .kamal/secrets with actual values (not $VAR forwarding)
chmod 600 .kamal/secrets
# Never commit this file
```

## Application Security Baseline

These controls are repository configuration only until a reviewed deploy occurs:

- Fastify accepts request bodies up to **4096 bytes**. A complete compact reading is only a few hundred bytes, so this leaves formatting headroom without retaining Fastify's 1 MiB default. Oversized requests receive HTTP 413 before database work.
- `POST /v1/ingest` keeps the existing generic 403 contract and compares the shared ingest key through fixed-size SHA-256 digests with `timingSafeEqual`.
- Request logging redacts `x-api-key`, `authorization`, `cookie`, and `set-cookie` values. Never add those values to messages, query strings, or differently named log fields.
- `@fastify/helmet` supplies API-appropriate security headers. Content Security Policy and Cross-Origin Resource Policy are disabled because this service returns public JSON rather than HTML and must not impose browser resource policy on consumers.
- Public read/health routes share a limit of **60 requests per minute per resolved client IP**. Ingest has a separate limit of **120 requests per minute per resolved client IP**, which is comfortably above the normal 12 readings/hour cadence and the outdoor station's roughly eight-reading offline replay buffer.
- Limits use the plugin's in-memory store. They reset on application restart and are correct for the current single web container. Add a shared store and re-evaluate effective limits before running multiple application replicas.

### Proxy trust invariant

`proxy.forward_headers: false` is explicit in `config/deploy.yml`. With this setting, kamal-proxy v0.9.2 clears client-supplied `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` values, then generates clean values from the socket-observed client connection. Fastify additionally trusts forwarded addresses only when hop 0 is a private/local immediate peer, and it never trusts later hops. A direct public socket therefore cannot make Fastify trust its `X-Forwarded-For` header.

This model depends on port 3000 remaining unpublished and the application being reachable only from kamal-proxy on the private Kamal network. Re-verify forwarding behavior on kamal-proxy upgrades. Adding Cloudflare or another upstream proxy would expose that edge proxy's address to the application, not the original client address, until the entire proxy chain is redesigned and revalidated. Also re-evaluate before adding multiple application hosts.

### Fleet credential gate

One high-entropy shared ingest key is acceptable only for the initial small fleet. Before gateways grow materially, provision per-device/gateway credentials bound to allowed `device_id` values and support individual revocation. Do not weaken the global key or encode it in logs, URLs, or source control.

## Database Startup Retry

Startup migrations make at most **four attempts**, with exponential delays of **250 ms, 500 ms, and 1000 ms** and a **12-second elapsed guard**. Each startup migration connection has a two-second connection timeout, so a continuously unavailable local database normally fails in under ten seconds rather than relying on an unbounded container restart loop.

Only explicit transient connection codes are retried: refused/reset/aborted connections, broken pipes, temporary DNS failure (`EAI_AGAIN`), network/host unreachable or down, postgres.js connection timeout/closed/destroyed errors, and PostgreSQL `08001`, `08006`, or `57P03`. Nested `cause` values are inspected, and an `AggregateError` is retryable only when every contained error is transient. Permanent DNS failure (`ENOTFOUND`), invalid URLs/configuration, authentication failures, and SQL/migration/schema errors fail immediately.

Retry logs contain only attempt count, delay, and error code—never the database URL, message, or credentials. A shutdown signal aborts an in-progress backoff instead of scheduling another attempt.

Backup, isolated-only restore testing, manual production-recovery gates, and uninstalled systemd timer templates are documented in [PostgreSQL Backup and Restore Runbook](postgres-backup-restore.md).

## First Deploy

First deployment to a fresh host sets up the proxy and accessories:

```bash
export KAMAL_HOST=192.168.1.50
bin/deploy setup
```

Subsequent deployments:

```bash
export KAMAL_HOST=192.168.1.50
bin/deploy
```

## Operations

All `bundle exec kamal ...` commands below assume `KAMAL_HOST` is exported in the current shell (or prefixed on each command). If absent, the config falls back to `placeholder.local`.

| Command | Purpose |
|---|---|
| `KAMAL_HOST=192.168.1.50 bin/deploy` | Full deploy (CI + deploy) |
| `KAMAL_HOST=192.168.1.50 bin/deploy setup` | First-time setup (proxy + accessories + deploy) |
| `bundle exec kamal app logs` | Tail application logs |
| `bundle exec kamal accessory logs postgres` | Tail PostgreSQL logs |
| `bundle exec kamal details` | Show deployment status |
| `bundle exec kamal app boot` | Start application containers |
| `bundle exec kamal app stop` | Stop application containers |
| `bundle exec kamal app remove` | Remove application from host (data preserved) |
| `bundle exec kamal accessory remove postgres` | Remove PostgreSQL container (data preserved) |
| `bundle exec kamal app images` | List available release images |
| `bundle exec kamal redeploy` | Zero-downtime redeploy (pulls new image, replaces containers) |
| `bundle exec kamal rollback <VERSION>` | Rollback to a specific release (discover versions via `app images`) |
| `bin/backup-postgres` | Create and retain a validated local logical backup |
| `bin/restore-postgres --archive <absolute-path>` | Restore into a generated isolated database |
| `bin/test-backup-restore --archive <absolute-path>` | Manually prove a live isolated restore (not normal CI) |

## Teardown Guardrails

- Do **not** destroy `/var/lib/zephyr` without a verified backup and restore test
- Do **not** retire AWS/Supabase until all consumers (gateway, iOS, web assistant) have been cut over and observed for several days
- Do **not** expose public DNS or TLS until network decisions are confirmed
- Keep GHCR images and Git branches for at least two releases to enable rollback
- PostgreSQL data lives in `/var/lib/zephyr/postgres` on the host; container replacement does not erase it
- `bundle exec kamal remove` removes proxy, app, accessories, and registry session — this is a full teardown, not app-only removal
