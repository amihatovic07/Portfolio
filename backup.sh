#!/bin/bash
cd "$(dirname "$0")"

if [ -f "./instance/portfolio.db" ]; then
    DB_PATH="./instance/portfolio.db"
elif [ -f "./portfolio.db" ]; then
    DB_PATH="./portfolio.db"
else
    echo "GREŠKA: portfolio.db nije pronađen ni u instance/ ni u rootu."
    exit 1
fi

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$BACKUP_DIR/backup.log"

mkdir -p "$BACKUP_DIR"

cp "$DB_PATH" "$BACKUP_DIR/portfolio_$TIMESTAMP.db"

{
    echo "===== BACKUP $TIMESTAMP ====="
    echo ""
    echo "--- PROJEKT ---"
    sqlite3 "$DB_PATH" -header -column "SELECT id, naziv, jezik, opis, status, link FROM projekt;"
    echo ""
    echo "--- OBJAVA ---"
    sqlite3 "$DB_PATH" -header -column "SELECT id, naziv, tekst, slika, datum_objave FROM objava;"
    echo ""
    echo "--- SLIKA ---"
    sqlite3 "$DB_PATH" -header -column "SELECT id, slika, u_carouselu, projekt_id FROM slika;"
    echo ""
} >> "$LOG_FILE"

echo "Backup gotov: $BACKUP_DIR/portfolio_$TIMESTAMP.db"
echo "Detaljan log: $LOG_FILE"
