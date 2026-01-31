#!/bin/bash
set -e

# Configuration
DATA_DIR="/app/data"
DB_FILE="${DATA_DIR}/sedaye_ma.db"
BACKUP_DIR="${DATA_DIR}/backups"
MAX_BACKUPS=5

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

if [ -f "$DB_FILE" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="${BACKUP_DIR}/sedaye_ma_backup_${TIMESTAMP}.db"
    
    echo "Creating database backup: $BACKUP_FILE"
    cp "$DB_FILE" "$BACKUP_FILE"
    
    # Keep only the last N backups
    cd "$BACKUP_DIR"
    ls -t sedaye_ma_backup_*.db | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm
    cd - > /dev/null
else
    echo "No database found at $DB_FILE. Skipping backup."
fi

# Execute the main command
exec "$@"
