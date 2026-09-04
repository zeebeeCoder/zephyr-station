# Disabled public-origin DNS project

The former `zephyr-dns` Pulumi project that declared a public origin `A` record is intentionally removed from active repository scope. It was never initialized, previewed, or applied, and there is no stack to destroy.

The approved API path is private:

- household DNS resolves the host's Tailscale certificate hostname to `192.168.1.50`;
- no public Zephyr origin record exposes the server;
- no WAN TCP forwarding is created for Zephyr;
- publicly trusted certificates come from Tailscale, not Cloudflare DNS-01.

The removed public-A implementation remains available in Git history at commits `4bde94a` and `551ad37`. Restoring it requires a new owner-approved architecture decision and code review. This directory deliberately contains no `Pulumi.yaml`, provider dependency, program entrypoint, stack instructions, or apply command.
