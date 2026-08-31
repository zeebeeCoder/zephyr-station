# PostgreSQL Backup and Restore Runbook

Repository tooling only. The systemd templates are not installed or enabled by this change.

## Recovery model

`bin/backup-postgres` runs PostgreSQL 17 `pg_dump --format=custom` inside the PostgreSQL container. The default host root is `/var/lib/zephyr/backups`:

```text
backups/
  .maintenance.lock
  daily/20260831T010203Z/{zephyr.dump,SHA256SUMS,COMPLETE}
  weekly/2026-W35/{zephyr.dump,SHA256SUMS,COMPLETE}
```

A point becomes visible through one atomic directory rename. `COMPLETE` is written last before that rename. Files are mode 600; directories and the dedicated, canonical, non-symlink `backups` root are mode 700.

Keep seven newest daily points and four newest weekly points. The first successful backup in each ISO week creates that week's point on any weekday, using a hardlink to the daily archive. Missing a scheduled day therefore does not create a weekly gap.

These host-local backups protect against bad SQL and accidental database changes, not host/disk loss. Off-machine replication is still required for disaster recovery.

## Backup

Non-secret configuration:

| Variable | Default |
|---|---|
| `ZEPHYR_POSTGRES_CONTAINER` | `zephyr-postgres` |
| `ZEPHYR_POSTGRES_DATABASE` | `zephyr` |
| `ZEPHYR_POSTGRES_USER` | `zephyr` |
| `ZEPHYR_BACKUP_ROOT` | `/var/lib/zephyr/backups` |

```bash
bin/backup-postgres
```

The command:

1. Requires the existing backup root to be mode 700, then acquires `.maintenance.lock` with nonblocking FD-based `flock`.
2. Dumps to a private temporary directory on the daily filesystem.
3. Requires nonempty output and validates it with container `pg_restore --list`.
4. Writes basename-only `SHA256SUMS`, then `COMPLETE`, then atomically renames the point directory.
5. Creates the ISO-week point only when that week has no point yet.
6. Audits every daily/weekly point's canonical name, directory mode 700, exact three-file shape and mode 600, checksum, marker, and archive list.
7. Prunes whole directories only when the complete audit succeeds.

An old corrupt, malformed, incomplete, mounted, or unexpected temporary point does not block today's publication. The command keeps the new point, preserves every old point, skips all pruning, prints a retention-review error, and exits nonzero. Pruning unlinks only the three audited files and removes the empty point directory; it never recursively deletes a recovery point. Resolve anomalies manually; never delete a questionable point merely to make the timer green.

Verify one point manually:

```bash
cd /var/lib/zephyr/backups/daily/20260831T010203Z
sha256sum --check SHA256SUMS
```

## Isolated restore only

The executable restore command always refuses the configured production database. It accepts only a complete point below the configured backup root and restores to a `zephyr_restore_*` database:

```bash
bin/restore-postgres \
  --archive /var/lib/zephyr/backups/daily/20260831T010203Z/zephyr.dump

bin/restore-postgres \
  --archive /var/lib/zephyr/backups/weekly/2026-W35/zephyr.dump \
  --target zephyr_restore_manual
```

An existing isolated target requires explicit replacement:

```bash
bin/restore-postgres \
  --archive /var/lib/zephyr/backups/daily/20260831T010203Z/zephyr.dump \
  --target zephyr_restore_manual \
  --replace
```

Backup and restore share `.maintenance.lock`. Restore validates the path, canonical point name, exact file shape, checksum, `COMPLETE`, and `pg_restore --list` before database changes. It uses `--exit-on-error --no-owner --no-privileges` and attempts to drop a partial target after failure.

Production cutover is deliberately outside v1 automation. First prove an isolated restore. Any later production recovery/cutover requires a separately approved maintenance plan, stopped writers, fresh pre-recovery backup, reviewed SQL, rollback plan, and owner authorization. Do not point this script at production; it will refuse.

## Restore proofs

`bin/ci` creates an actual custom-format backup from its ephemeral Compose PostgreSQL, restores it to an isolated database, compares it with the source, and removes the target. The comparison covers device/readings counts, timestamp bounds, latest representative fields, and an anchored 24-hour history aggregate.

A separately approved staging proof remains required before relying on host backups:

```bash
bin/test-backup-restore \
  --archive /var/lib/zephyr/backups/daily/20260831T010203Z/zephyr.dump
```

Run it promptly after a fresh backup during a no-write window. It fingerprints the source before and after restore; concurrent source changes make the proof inconclusive. It never replaces production and always attempts to remove its isolated target.

## systemd templates

- `config/systemd/zephyr-postgres-backup.service`
- `config/systemd/zephyr-postgres-backup.timer`

The timer is persistent and runs nightly at 02:15 UTC. The service has a bounded 15-minute timeout, runs as `sagent`, and uses `UMask=0077`. A missing host path is not treated as a successful skip: setup or permission failures make the unit fail observably.

**Docker access is root-equivalent.** Membership in the Docker group can control host containers and mounts. Installation requires host review of the user, group membership, checkout path, backup ownership, timeout, and schedule.

After separate approval only:

```bash
sudo install -d -o sagent -g sagent -m 700 /var/lib/zephyr/backups
sudo install -m 644 config/systemd/zephyr-postgres-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zephyr-postgres-backup.timer
```

Inspect without changing data:

```bash
systemctl status zephyr-postgres-backup.timer
systemctl list-timers zephyr-postgres-backup.timer
journalctl -u zephyr-postgres-backup.service
```

Disable scheduling without deleting recovery points:

```bash
sudo systemctl disable --now zephyr-postgres-backup.timer
sudo rm -f /etc/systemd/system/zephyr-postgres-backup.{service,timer}
sudo systemctl daemon-reload
```
