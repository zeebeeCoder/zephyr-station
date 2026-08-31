# Disabled public-origin DNS project

The former `zephyr-dns` Pulumi project that declared a public origin `A` record is intentionally removed from active repository scope. It was never initialized, previewed, or applied, and there is no stack to destroy.

The approved API path is private:

- `zephyr.home.dicr.tech` resolves only through household private DNS to `192.168.1.50`;
- no public `A`, `AAAA`, or `CNAME` exposes the Zephyr origin;
- no WAN TCP forwarding is created for Zephyr;
- publicly trusted certificates will use a separately reviewed Cloudflare DNS-01 ACME flow that creates temporary challenge `TXT` records only.

The removed public-A implementation remains available in Git history at commits `4bde94a` and `551ad37`. Restoring it requires a new owner-approved architecture decision and code review. This directory deliberately contains no `Pulumi.yaml`, provider dependency, program entrypoint, stack instructions, or apply command.
