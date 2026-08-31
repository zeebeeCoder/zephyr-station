# Zephyr Cloudflare DNS

Dedicated Pulumi Cloud project for the Zephyr public API DNS record. This project is intentionally isolated from the legacy AWS project in `infrastructure/`; it has no AWS provider, resources, configuration, or state.

## Ownership boundary

Project `zephyr-dns` declares exactly one `cloudflare:index/dnsRecord:DnsRecord` named `zephyr-api-a` in an existing external zone:

- one `A` record using the approved `zephyr` label and an explicitly configured full hostname;
- one explicitly configured public origin IPv4;
- DNS-only (`proxied: false`);
- TTL 300 seconds;
- no `AAAA`, zone, zone setting, TLS, Worker, Page, Rule, or frontend resource.

A `DnsRecord` manages only the record ID in this project's Pulumi state. It is not an authoritative collection of zone records: the root website and every unrelated DNS record remain outside this project. The zone itself is never created, imported, or managed.

## Prerequisites

- Node.js 22 or newer.
- Pulumi CLI 3.260.x is recommended to match the pinned Pulumi SDK. The CLI must be installed separately through an approved system-tooling step.
- A Pulumi Cloud account and approved organization.

## State and authentication

Use Pulumi Cloud's default managed state and secrets service. Do not use `--local`, a `file://` backend, or the legacy AWS project's empty-passphrase setup.

The Cloudflare token is environment-only and must never be placed in Pulumi config, stack outputs, source, or logs:

```bash
export CLOUDFLARE_API_TOKEN="$CF_TOKEN"
```

`CF_ACCOUNT_ID` is not required or read: this project manages a zone-scoped DNS record only.

## One-time project and stack setup

The intended stack is `prod`. Replace the organization placeholder; do not create or select a stack until explicitly approved:

```bash
cd infrastructure/cloudflare-dns
npm ci
pulumi login
pulumi stack select '<pulumi-org>/zephyr-dns/prod'
# If the approved stack does not exist:
pulumi stack init '<pulumi-org>/zephyr-dns/prod'
```

Configure all three non-secret inputs explicitly. The hostname must be the approved `zephyr` label under the existing zone; do not infer the domain or origin from local files:

```bash
pulumi config set cloudflareZoneId "$CF_DOMAIN_ZONE_ID"
pulumi config set apiHostname '<approved-zephyr-api-hostname>'
pulumi config set originIpv4 '<approved-static-public-ipv4>'
```

No `Pulumi.prod.yaml` is committed before approved stack setup.

## Discover and import before ownership

Strict read-only inventory for the approved exact hostname is complete: no `A`, `AAAA`, `CNAME`, or other record currently exists there. No import is currently required, and the expected preview is exactly one create. Re-check the exact hostname immediately before an approved preview/apply if time has passed or configuration has changed.

The ownership rule remains:

- If the re-check still finds no exact record, preview one create.
- If a record exists, obtain its record ID and import it before Pulumi assumes ownership.
- If conflicting or multiple records exist at the hostname, stop. Do not import, replace, or duplicate anything.

Import is a live Pulumi state operation and requires separate explicit approval:

```bash
pulumi import cloudflare:index/dnsRecord:DnsRecord zephyr-api-a \
  "${CF_DOMAIN_ZONE_ID}/${CF_DNS_RECORD_ID}"
```

## Validate and preview gate

Local deterministic validation does not need a Pulumi Cloud stack:

```bash
npm ci
npm run check
npm test
npm run build
```

After stack setup, input approval, and any required import are separately authorized, the preview command is:

```bash
pulumi preview --diff
```

Proceed only if the complete preview shows exactly the intended `zephyr-api-a` change, with type `A`, `proxied: false`, TTL 300, the approved hostname/origin, and no delete or replacement. A pre-existing record must not be proposed as a duplicate. No token or credential may appear in the preview.

`pulumi up` is not part of this runbook and must not be run without separate explicit approval of the exact preview. DNS approval does not authorize Cloudflare proxying, UDM/network changes, TLS enablement, Kamal deployment, or consumer cutover.

## Rollback

Keep the legacy AWS API and consumer endpoints intact during rollout. Record the prior DNS target before an approved change.

- For an imported record, restore the prior target through config and a separately reviewed preview/apply.
- For a newly created record, remove its declaration only through a separately reviewed code change and apply.
- Never mutate the external zone, root website, or unrelated records as part of rollback.
