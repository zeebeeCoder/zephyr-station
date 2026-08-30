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

## Teardown Guardrails

- Do **not** destroy `/var/lib/zephyr` without a verified backup and restore test
- Do **not** retire AWS/Supabase until all consumers (gateway, iOS, web assistant) have been cut over and observed for several days
- Do **not** expose public DNS or TLS until network decisions are confirmed
- Keep GHCR images and Git branches for at least two releases to enable rollback
- PostgreSQL data lives in `/var/lib/zephyr/postgres` on the host; container replacement does not erase it
- `bundle exec kamal remove` removes proxy, app, accessories, and registry session — this is a full teardown, not app-only removal
