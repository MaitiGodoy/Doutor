#!/usr/bin/env bash
# backup_auto.sh – Daily backup of SQLite databases, logs, config, and state.
set -euo pipefail

KERNEL_DIR="/root/doutor-kernel"
BACKUP_ROOT="${BACKUP_ROOT:-/root/backups}"
DATE_TAG="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/doutor_${DATE_TAG}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
S3_BUCKET="${S3_BUCKET:-}"
LOG_FILE="${BACKUP_ROOT}/backup_${DATE_TAG}.log"

mkdir -p "${BACKUP_DIR}" "${BACKUP_DIR}/sqlite" "${BACKUP_DIR}/logs" "${BACKUP_DIR}/config" "${BACKUP_DIR}/state"

exec > >(tee -a "${LOG_FILE}") 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup to ${BACKUP_DIR}"

# 1. Find and backup all SQLite databases
echo "--- SQLite databases ---"
find "${KERNEL_DIR}" -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" 2>/dev/null | while read -r db; do
    rel_path="${db#${KERNEL_DIR}/}"
    dest="${BACKUP_DIR}/sqlite/${rel_path//\//_}"
    echo "  Backing up ${rel_path} -> $(basename "${dest}")"
    sqlite3 "${db}" ".backup '${dest}'" 2>/dev/null || cp "${db}" "${dest}"
done

# 2. Backup logs (last 7 days)
echo "--- Logs ---"
if [ -d "${KERNEL_DIR}/logs" ]; then
    tar czf "${BACKUP_DIR}/logs/logs_${DATE_TAG}.tar.gz" -C "${KERNEL_DIR}" logs/ --exclude="*.tar.gz" 2>/dev/null
    echo "  Logs archived: $(du -sh "${BACKUP_DIR}/logs/logs_${DATE_TAG}.tar.gz" | cut -f1)"
fi

# 3. Backup Docker volumes
echo "--- Docker volumes ---"
docker volume ls -q --filter name=doutor 2>/dev/null | while read -r vol; do
    dest="${BACKUP_DIR}/state/${vol}.tar.gz"
    echo "  Backing up volume: ${vol}"
    docker run --rm -v "${vol}":/volume -v "${BACKUP_DIR}/state":/backup alpine \
        tar czf "/backup/${vol}.tar.gz" -C /volume . 2>/dev/null || true
done

# 4. Backup config files
echo "--- Config files ---"
find "${KERNEL_DIR}" -maxdepth 3 \( -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.env" -o -name "*.cfg" -o -name "*.conf" \) 2>/dev/null | while read -r cfg; do
    rel="${cfg#${KERNEL_DIR}/}"
    mkdir -p "$(dirname "${BACKUP_DIR}/config/${rel}")"
    cp "${cfg}" "${BACKUP_DIR}/config/${rel}"
done
echo "  Configs backed up"

# 5. Save docker-compose state
echo "--- Docker compose state ---"
docker compose -f "${KERNEL_DIR}/docker-compose.yml" ps --format json > "${BACKUP_DIR}/state/docker_ps.json" 2>/dev/null || true
docker inspect doutor-v41 > "${BACKUP_DIR}/state/container_inspect.json" 2>/dev/null || true

# 6. Save git commit hash
git -C "${KERNEL_DIR}" rev-parse HEAD > "${BACKUP_DIR}/state/git_commit.txt" 2>/dev/null || true

# 7. Create manifest
cat > "${BACKUP_DIR}/MANIFEST.txt" << EOFMANIFEST
Backup:      doutor_${DATE_TAG}
Created:     $(date '+%Y-%m-%d %H:%M:%S')
Kernel:      ${KERNEL_DIR}
Git Commit:  $(git -C "${KERNEL_DIR}" rev-parse HEAD 2>/dev/null || echo "unknown")
Host:        $(hostname)
Size:        $(du -sh "${BACKUP_DIR}" | cut -f1)
Files:       $(find "${BACKUP_DIR}" -type f | wc -l)
EOFMANIFEST

echo "---"
echo "Backup size: $(du -sh "${BACKUP_DIR}" | cut -f1)"
echo "Backup files: $(find "${BACKUP_DIR}" -type f | wc -l)"

# 8. Prune old backups
echo "--- Pruning backups older than ${RETENTION_DAYS} days ---"
find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "doutor_*" -mtime "+${RETENTION_DAYS}" -exec rm -rf {} \; -exec echo "  Removed old backup: {}" \;

# 9. Sync to S3 if configured
if [ -n "${S3_BUCKET}" ]; then
    echo "--- Syncing to S3: ${S3_BUCKET} ---"
    aws s3 sync "${BACKUP_DIR}" "${S3_BUCKET}/doutor_${DATE_TAG}/" --no-progress 2>/dev/null || \
        echo "  WARNING: S3 sync failed (aws-cli not configured?)"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete: ${BACKUP_DIR}"
