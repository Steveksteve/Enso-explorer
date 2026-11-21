#!/usr/bin/env sh
# Sauvegarde quotidienne de PostgreSQL (à lancer par cron sur le VPS) :
#   15 3 * * * /opt/enso-explorer/deploy/backup.sh >> /var/log/enso-backup.log 2>&1
# Restauration :
#   gunzip -c backups/enso_AAAAMMJJ_HHMM.sql.gz | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
set -eu
cd "$(dirname "$0")/.."
. ./.env
mkdir -p backups
FILE="backups/enso_$(date +%Y%m%d_%H%M).sql.gz"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists | gzip > "$FILE"
# Conserver 14 jours de sauvegardes locales (copie hors serveur recommandée : rclone/rsync)
find backups -name 'enso_*.sql.gz' -mtime +14 -delete
echo "$(date -Iseconds) sauvegarde OK : $FILE"
