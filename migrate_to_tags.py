import sqlite3
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pronađi trenutnu bazu (lokalno je u instance/, na serveru u rootu)
if os.path.exists(os.path.join(BASE_DIR, "instance", "portfolio.db")):
    CURRENT_DB = os.path.join(BASE_DIR, "instance", "portfolio.db")
elif os.path.exists(os.path.join(BASE_DIR, "portfolio.db")):
    CURRENT_DB = os.path.join(BASE_DIR, "portfolio.db")
else:
    print("GREŠKA: portfolio.db nije pronađen ni u instance/ ni u rootu.")
    sys.exit(1)

OLD_DB = CURRENT_DB + ".old"

print(f"Koristim bazu: {CURRENT_DB}")

# --- 1) Pročitaj sve stare podatke prije nego se baza dira ---
conn = sqlite3.connect(CURRENT_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

stari_projekti = cur.execute(
    "SELECT id, naziv, jezik, opis, status, link FROM projekt"
).fetchall()
stare_objave = cur.execute(
    "SELECT id, naziv, tekst, slika, datum_objave FROM objava"
).fetchall()
stare_slike = cur.execute(
    "SELECT id, slika, u_carouselu, projekt_id FROM slika"
).fetchall()

conn.close()

print(f"Pročitano: {len(stari_projekti)} projekata, {len(stare_objave)} objava, {len(stare_slike)} slika.")

# --- 2) Skloni staru bazu s puta, da app.py napravi svježu shemu ---
os.rename(CURRENT_DB, OLD_DB)

# --- 3) Uvoz app.py sad pokreće db.create_all() nad NOVOM (praznom) bazom ---
from app import app, db, projekt, objava, slika, tag

with app.app_context():
    db.create_all()

    # Ponovno upiši projekte, pretvarajući stari 'jezik' u tag(ove)
    for p in stari_projekti:
        novi = projekt(
            id=p["id"],
            naziv=p["naziv"],
            opis=p["opis"],
            status=p["status"],
            link=p["link"]
        )
        nazivi_tagova = [t.strip() for t in p["jezik"].split(",") if t.strip()]
        tagovi_objekti = []
        for naziv in nazivi_tagova:
            t = tag.query.filter(db.func.lower(tag.naziv) == naziv.lower()).first()
            if not t:
                t = tag(naziv=naziv)
                db.session.add(t)
                db.session.flush()
            tagovi_objekti.append(t)
        novi.tagovi = tagovi_objekti
        db.session.add(novi)

    # Objave ostaju identične, samo se prenose
    for o in stare_objave:
        datum = o["datum_objave"]
        if isinstance(datum, str):
            try:
                datum = datetime.strptime(datum, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                datum = datetime.strptime(datum, "%Y-%m-%d %H:%M:%S")

        db.session.add(objava(
            id=o["id"],
            naziv=o["naziv"],
            tekst=o["tekst"],
            slika=o["slika"],
            datum_objave=datum
        ))

    # Slike ostaju identične, samo se prenose (sami fajlovi već su na disku)
    for s in stare_slike:
        db.session.add(slika(
            id=s["id"],
            slika=s["slika"],
            u_carouselu=bool(s["u_carouselu"]),
            projekt_id=s["projekt_id"]
        ))

    db.session.commit()
    print("Migracija gotova! Svi projekti, objave i slike su preneseni u novu shemu s tagovima.")

os.remove(OLD_DB)
print("Privremena stara baza obrisana (backup.sh kopija i dalje sigurno postoji u backups/).")