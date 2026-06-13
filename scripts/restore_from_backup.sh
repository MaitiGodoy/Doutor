#!/usr/bin/env bash
set -euo pipefail
KERNEL_DIR="/root/doutor-kernel"
BACKUP_ROOT=${BACKUP_ROOT:-/root/backups}
LIST=false; SQLITE=true; LOGS=true; CONFIG=true; VOLS=true; FORCE=false; BDIR=""
while [[ $# -gt 0 ]]; do case "$1" in
--list) LIST=true; shift ;; --backup) BDIR="$2"; shift 2 ;;
--sqlite-only) LOGS=false; CONFIG=false; VOLS=false; shift ;;
--logs-only) SQLITE=false; CONFIG=false; VOLS=false; shift ;;
--config-only) SQLITE=false; LOGS=false; VOLS=false; shift ;;
--volumes-only) SQLITE=false; LOGS=false; CONFIG=false; shift ;;
--force) FORCE=true; shift ;; --help|-h) usage ;; *) usage ;;
esac; done
if $LIST; then find "$BACKUP_ROOT" -maxdepth 1 -type d -name "doutor_*" | sort -r | while read -r b; do echo "  $(basename $b)"; done; exit 0; fi
[ -z "$BDIR" ] && BDIR=$(find "$BACKUP_ROOT" -maxdepth 1 -type d -name "doutor_*" | sort -r | head -1)
[ -z "$BDIR" ] && { echo "No backups found"; exit 1; }
echo "Restoring: $BDIR"; $FORCE || read -p "Continue? [Enter] " x
docker compose -f "$KERNEL_DIR/docker-compose.yml" down 2>/dev/null || true
$SQLITE && [ -d "$BDIR/sqlite" ] && find "$BDIR/sqlite" -type f | while read -r f; do
    o=$(find "$KERNEL_DIR" -name "*.db" | head -1); [ -z "$o" ] && { mkdir -p "$KERNEL_DIR/data"; o="$KERNEL_DIR/data/restored.db"; }; cp "$f" "$o"
done
$LOGS && for a in "$BDIR"/logs/*.tar.gz; do [ -f "$a" ] && tar xzf "$a" -C "$KERNEL_DIR" 2>/dev/null || true; done
$CONFIG && cp -r "$BDIR/config/"* "$KERNEL_DIR/" 2>/dev/null || true
$VOLS && for a in "$BDIR"/state/doutor*.tar.gz; do [ -f "$a" ] || continue; v=$(basename "$a" .tar.gz); docker volume create "$v" 2>/dev/null || true; docker run --rm -v "$v":/volume -v "$BDIR/state":/backup alpine tar xzf "/backup/$(basename $a)" -C /volume 2>/dev/null || true; done
docker compose -f "$KERNEL_DIR/docker-compose.yml" up -d 2>/dev/null || true
echo "Restore complete"