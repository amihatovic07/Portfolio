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
    sqlite3 "$DB_PATH" -header -column "SELECT p.id, p.naziv, GROUP_CONCAT(t.naziv, ', ') AS tagovi, p.opis, p.status, p.link FROM projekt p LEFT JOIN projekt_tagovi pt ON pt.projekt_id = p.id LEFT JOIN tag t ON t.id = pt.tag_id GROUP BY p.id;"
    echo ""
    echo "--- OBJAVA ---"
    sqlite3 "$DB_PATH" -header -column "SELECT id, naziv, tekst, slika, datum_objave FROM objava;"
    echo ""
    echo "--- SLIKA ---"
    sqlite3 "$DB_PATH" -header -column "SELECT id, slika, u_carouselu, projekt_id FROM slika;"
    echo ""
} >> "$LOG_FILE" 2>&1

echo "Backup gotov: $BACKUP_DIR/portfolio_$TIMESTAMP.db"
echo "Detaljan log: $LOG_FILE"
