#!/usr/bin/env bash

zephyr_die() {
  echo "ERROR: $*" >&2
  exit 1
}

zephyr_require_command() {
  command -v "$1" >/dev/null 2>&1 || zephyr_die "Required command not found: $1"
}

zephyr_validate_container_name() {
  [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || zephyr_die "Unsafe container name"
}

zephyr_validate_database_name() {
  [[ "$1" =~ ^[A-Za-z_][A-Za-z0-9_]{0,62}$ ]] || zephyr_die "Unsafe database/user name"
}

zephyr_validate_absolute_path() {
  [[ "$1" =~ ^/[A-Za-z0-9._/-]+$ ]] || zephyr_die "Path must be absolute and contain only safe characters"
  case "$1" in
    /|*/|*//*|*/./*|*/.|*/../*|*/..) zephyr_die "Unsafe path" ;;
  esac
}

zephyr_validate_backup_root() {
  local canonical
  zephyr_validate_absolute_path "$1"
  [[ "$1" == */backups ]] || zephyr_die "Backup root must be a dedicated directory named backups"
  canonical=$(realpath -m -- "$1")
  [ "$canonical" = "$1" ] || zephyr_die "Backup root must not traverse symlinks"
}

zephyr_validate_point_name() {
  local family=$1 name=$2 stamp year month day hour minute second week canonical

  if [ "$family" = daily ] && [[ "$name" =~ ^([0-9]{8}T[0-9]{6}Z)$ ]]; then
    stamp=${BASH_REMATCH[1]}
    year=${stamp:0:4}; month=${stamp:4:2}; day=${stamp:6:2}
    hour=${stamp:9:2}; minute=${stamp:11:2}; second=${stamp:13:2}
    canonical=$(date -u -d "$year-$month-$day $hour:$minute:$second" +%Y%m%dT%H%M%SZ 2>/dev/null) \
      || zephyr_die "Invalid daily recovery-point name: $name"
    [ "$canonical" = "$name" ] || zephyr_die "Non-canonical daily recovery-point name: $name"
    return
  fi

  if [ "$family" = weekly ] && [[ "$name" =~ ^([0-9]{4})-W([0-9]{2})$ ]]; then
    year=${BASH_REMATCH[1]}; week=${BASH_REMATCH[2]}
    canonical=$(date -u -d "$year-01-04 +$((10#$week - 1)) weeks" +%G-W%V 2>/dev/null) \
      || zephyr_die "Invalid weekly recovery-point name: $name"
    [ "$canonical" = "$name" ] || zephyr_die "Non-canonical weekly recovery-point name: $name"
    return
  fi

  zephyr_die "Malformed $family recovery-point name: $name"
}

zephyr_validate_point_files() {
  local point=$1 archive checksum complete line digest actual
  archive="$point/zephyr.dump"
  checksum="$point/SHA256SUMS"
  complete="$point/COMPLETE"

  [ -d "$point" ] && [ ! -L "$point" ] || zephyr_die "Recovery point is not a real directory: $point"
  ! mountpoint -q -- "$point" || zephyr_die "Recovery point must not be a mount point: $point"
  [ "$(stat -c %a "$point")" = 700 ] || zephyr_die "Recovery point must be mode 700: $point"
  [ -f "$archive" ] && [ ! -L "$archive" ] && [ -s "$archive" ] || zephyr_die "Recovery archive is missing or unsafe: $point"
  [ -f "$checksum" ] && [ ! -L "$checksum" ] || zephyr_die "Recovery checksum is missing or unsafe: $point"
  [ -f "$complete" ] && [ ! -L "$complete" ] && [ ! -s "$complete" ] || zephyr_die "Recovery COMPLETE marker is missing or unsafe: $point"
  for file in "$archive" "$checksum" "$complete"; do
    [ "$(stat -c %a "$file")" = 600 ] || zephyr_die "Recovery files must be mode 600: $point"
  done
  [ "$(find "$point" -mindepth 1 -maxdepth 1 -printf . | wc -c)" -eq 3 ] || zephyr_die "Recovery point contains unexpected files: $point"

  [ "$(awk 'END { print NR }' "$checksum")" -eq 1 ] || zephyr_die "SHA256SUMS must contain exactly one line"
  line=$(<"$checksum")
  [[ "$line" =~ ^([0-9a-f]{64})\ \ zephyr\.dump$ ]] || zephyr_die "SHA256SUMS has unsafe content"
  digest=${BASH_REMATCH[1]}
  actual=$(sha256sum "$archive"); actual=${actual%% *}
  [ "$actual" = "$digest" ] || zephyr_die "Recovery archive checksum mismatch: $point"
}

zephyr_validate_recovery_archive() {
  local root=$1 archive=$2 point family name
  zephyr_validate_backup_root "$root"
  zephyr_validate_absolute_path "$archive"
  [ "$(realpath -m -- "$archive")" = "$archive" ] || zephyr_die "Archive path must not traverse symlinks"

  point=$(dirname "$archive")
  family=$(basename "$(dirname "$point")")
  name=$(basename "$point")
  [ "$archive" = "$root/$family/$name/zephyr.dump" ] || zephyr_die "Archive must be inside the configured backup root"
  case "$family" in daily|weekly) ;; *) zephyr_die "Archive must belong to a daily or weekly recovery point" ;; esac
  zephyr_validate_point_name "$family" "$name"
  zephyr_validate_point_files "$point"
}

zephyr_acquire_maintenance_lock() {
  local root=$1 lock="$1/.maintenance.lock"
  [ -d "$root" ] && [ ! -L "$root" ] || zephyr_die "Backup root must be a real directory"
  [ "$(stat -c %a "$root")" = 700 ] || zephyr_die "Backup root must be mode 700"
  [ ! -L "$lock" ] || zephyr_die "Maintenance lock must not be a symlink"
  exec 9> "$lock"
  flock --exclusive --nonblock 9 || zephyr_die "Backup or restore maintenance is already running"
}
