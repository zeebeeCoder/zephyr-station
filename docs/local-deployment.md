# Private Deployment Runbook

Zephyr's approved client endpoint is `https://zephyr.home.dicr.tech`. It is private even though its certificate is publicly trusted:

```text
trusted LAN / IoT VLAN / WireGuard
  -> private DNS: zephyr.home.dicr.tech = 192.168.1.50
  -> TCP 443 -> kamal-proxy -> Fastify -> Docker-private PostgreSQL

operator -> Tailscale/SSH KAMAL_HOST -> Kamal
WAN -> no Zephyr forwarding
```

`KAMAL_HOST` is the SSH deployment address and remains independent of the client hostname. No repository command configures UDM DNS/firewall, Cloudflare, certificate issuance, or WAN forwarding.

## Prerequisites

- Private SSH to `sagent@<KAMAL_HOST>` is verified, preferably through Tailscale.
- Docker and the existing Kamal/PostgreSQL deployment are healthy.
- GHCR credentials have `repo` and `write:packages` access.
- Ruby/Bundler dependencies are installed with `bundle install`.
- A reviewed certificate full chain and matching private key cover `zephyr.home.dicr.tech` and have at least 14 days remaining.
- `.kamal/secrets` is a regular, non-symlink mode-600 file when used.
- Private DNS and narrow TCP 443 rules are separately approved before client testing.

The custom certificate must come from the separately reviewed DNS-01 process. This repository does not yet issue or renew it. Kamal's hash-form `proxy.ssl` loads supplied PEM values and does **not** request a public Let's Encrypt challenge.

## Configuration and secrets

The approved hostname defaults to `zephyr.home.dicr.tech`. An explicit `ZEPHYR_PRIVATE_HOSTNAME` is accepted only when it exactly matches that value. Never use `KAMAL_HOST` as the TLS hostname.

Copy the forwarding template:

```bash
cp .kamal/secrets.example .kamal/secrets
chmod 600 .kamal/secrets
```

Supply these through an approved environment or secret source before running deployment commands:

- `KAMAL_REGISTRY_PASSWORD`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `INGEST_API_KEY`
- `ZEPHYR_TLS_CERTIFICATE_PEM` — leaf-first full chain
- `ZEPHYR_TLS_PRIVATE_KEY_PEM` — matching unencrypted deployment key

The TLS values are consumed by Kamal for proxy certificate files. They are not added to the application environment. Do not paste PEM content into source, command arguments, logs, tickets, or documentation.

Set the private deployment address and run the non-mutating preflight:

```bash
export KAMAL_HOST=100.108.58.19
export ZEPHYR_PRIVATE_HOSTNAME=zephyr.home.dicr.tech  # optional exact override
bin/deploy check
```

Preflight requires a clean tree; validates the secrets-file type/mode, certificate/key syntax and match, exact hostname SAN, and 14-day validity floor; then validates the Bundler and Kamal configuration. It suppresses raw PEM/OpenSSL/Kamal output.

## Private DNS and TLS boundary

Required external state, applied only through separate approval:

- UDM local DNS returns `192.168.1.50` for `zephyr.home.dicr.tech` to trusted, IoT, and WireGuard clients.
- Public resolvers return no Zephyr origin `A`, `AAAA`, or `CNAME`.
- Only the approved station/master can cross from IoT to `192.168.1.50:443`; DHCP, private DNS, and NTP remain available as required.
- WireGuard clients can reach private DNS and `192.168.1.50:443`.
- WAN TCP 22/80/443/3000/5432 remains closed; Tailscale remains the administration plane.

The removed `infrastructure/cloudflare-dns` public-A project must not be reconstructed or applied. DNS-01 certificate issuance uses temporary `_acme-challenge` TXT records only.

After private DNS/network approval, validate the certificate and route without publishing DNS by using a local override from an authorized client:

```bash
curl --fail --show-error \
  --resolve zephyr.home.dicr.tech:443:192.168.1.50 \
  https://zephyr.home.dicr.tech/up
```

Do not use `--insecure`. Verify SAN, issuer/chain, and expiry independently before consumer cutover.

## Application security baseline

- Fastify limits request bodies to 4096 bytes.
- Ingest retains the generic 403 contract and timing-safe digest comparison.
- Logs redact API keys, authorization, cookies, and response cookies.
- Helmet supplies API-appropriate headers.
- Private read/health routes are rate-limited in memory for the current single replica: 60 reads/minute/IP and 120 ingest requests/minute/IP.
- `proxy.forward_headers: false` makes kamal-proxy sanitize client forwarding headers; Fastify trusts only one private/local immediate proxy hop.
- Port 3000 stays unpublished and PostgreSQL remains reachable only on the Kamal Docker network.
- The shared ingest key is temporary for the small fleet; per-device credentials remain required before expansion.

Startup migration retries are bounded to four attempts, waits of 250/500/1000 ms, and a 12-second elapsed guard. Only explicit transient connectivity codes retry; logs omit connection strings and raw error messages.

## Backup gate

Application deployment does not install or invoke the backup timer. Before reliability acceptance or consumer cutover, the owner must:

1. create `/var/lib/zephyr/backups` as `sagent:sagent` mode 700;
2. run one reviewed staging backup and isolated restore proof;
3. separately review and install/enable the timer;
4. verify the first timer invocation.

See [PostgreSQL Backup and Restore Runbook](postgres-backup-restore.md). Missing backup storage is not permission to restore over production or delete PostgreSQL data.

## Deployment is temporarily check-only

This slice validates configuration but deliberately does not publish custom TLS. Kamal 2.12's default custom-key upload permissions are not acceptable for the private key, and issuance/renewal is not installed. Preserve the currently running `1ffd97a` staging deployment.

```bash
export KAMAL_HOST=100.108.58.19
bin/deploy check
```

`bin/deploy` and `bin/deploy setup` run the same preflight and then fail closed before CI or any mutating Kamal command. The later ACME slice must add and prove the restricted host TLS directory/publication hook and renewal path before re-enabling them. When live actions are restored, CI must run with registry, database, ingest, and both TLS PEM secrets explicitly removed from its subprocess environment.

## Verification

Keep writers/consumers on their previous endpoint until all approved checks pass:

1. `https://zephyr.home.dicr.tech/up` and `/ready` return 200 through private resolution.
2. `/v1/hello`, widget, and history preserve their contracts.
3. Authenticated ingest succeeds; missing/wrong keys, oversized bodies, and rate limits retain expected behavior.
4. Existing staging readings survive application replacement.
5. Application runs non-root and logs contain no secrets.
6. Host ports 3000/5432 remain unpublished; WAN probes remain closed.
7. Certificate SAN/chain/expiry validate from representative trusted, IoT, and WireGuard clients.
8. Public DNS does not disclose the origin.

Do not cut over ESP/iOS clients until DNS, TLS, routing, backup proof, and rollback are all approved.

## Operations and rollback

All Kamal commands require `KAMAL_HOST` and the custom TLS inputs because rendering is fail-closed.

| Command | Purpose |
|---|---|
| `bin/deploy check` | Validate clean tree, secrets, TLS, bundle, and Kamal config only |
| `bin/deploy` | Temporarily blocked after preflight; performs no live action |
| `bin/deploy setup` | Temporarily blocked after preflight; performs no live action |
| `bundle exec kamal details` | Show deployment status |
| `bundle exec kamal app logs` | Tail application logs |
| `bundle exec kamal accessory logs postgres` | Tail PostgreSQL logs |
| `bundle exec kamal app images` | List rollback image versions |
| `bundle exec kamal rollback <VERSION>` | Roll back application version |

Before a later approved deployment, record the current application version and retain its image. Application rollback must not remove PostgreSQL or its bind mount. Certificate rollback must restore a previously approved certificate/key version through the hardened publication path; never disable hostname validation or open WAN ports as a workaround.

Certificate issuance, restricted-key publication, renewal timers, expiry alerting, and safe proxy reload behavior require a later reviewed implementation and live proof. Until then, live actions remain blocked and this endpoint is not ready for consumer cutover.

## Teardown guardrails

- Never run full `kamal remove` as an app rollback; it removes proxy, app, accessories, and registry session.
- Never remove the PostgreSQL accessory or `/var/lib/zephyr` without approved backup/restore gates.
- Never expose 3000/5432, publish public API DNS, or create WAN forwarding.
- Keep AWS/Supabase and at least two GHCR application versions until private consumers are observed and retirement is separately approved.
