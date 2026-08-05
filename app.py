# Uvodni dio gdje se uvode biblioteke za rad
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
import secrets
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv

# Dio gdje se radi sa bazom podataka kako bi se formirala baza
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
db = SQLAlchemy(app)

# Dio za konfiguraciju passworda za ulazak unutar admin panela
load_dotenv()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
ADMIN_KOD = os.environ.get('ADMIN_KOD')

if not ADMIN_KOD:
    raise RuntimeError("ADMIN_KOD nije postavljen u .env datoteci.")

# Mapa u koju će se spremati slike
app.config["UPLOAD_FOLDER"] = os.path.join(
    app.static_folder,
    "uploads"
)

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Ograničenje veličine datoteke na 5 MB
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Dopuštene ekstenzije slika
DOZVOLJENE_EKSTENZIJE = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

# Ako mapa ne postoji, automatski se stvara
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# Formirana klasa projekt
class projekt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    naziv = db.Column(db.String(50), nullable=False)
    jezik = db.Column(db.String(40), nullable=False)
    opis = db.Column(db.String(400), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    link = db.Column(db.String(100), nullable=False)
    slike = db.relationship(
        "slika",
        backref="projekt",
        lazy=True,
        cascade="all, delete-orphan"
    )

# Formirana klasa objava
class objava(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    naziv = db.Column(db.String(50), nullable=False)
    tekst = db.Column(db.String(400), nullable=False)
    slika = db.Column(db.String(200), nullable=True)
    datum_objave = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Formirana klasa galerija
class slika(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slika = db.Column(db.String(200), nullable=True)
    u_carouselu = db.Column(db.Boolean, default=False)
    projekt_id = db.Column(
        db.Integer,
        db.ForeignKey("projekt.id"),
        nullable=False
    )

# Inicijalizirano generiranje svih klasa kao relacijske modele unutar baze podataka
with app.app_context():
    db.create_all()

# Funkcija provjerava ima li slika dopuštenu ekstenziju
def dozvoljena_slika(naziv_datoteke):
    return (
        "." in naziv_datoteke
        and naziv_datoteke.rsplit(".", 1)[1].lower()
        in DOZVOLJENE_EKSTENZIJE
    )


# Funkcija sprema sliku i vraća njezin novi naziv
def spremi_sliku(datoteka):
    if datoteka is None or datoteka.filename == "":
        return None

    siguran_naziv = secure_filename(datoteka.filename)

    if not siguran_naziv or not dozvoljena_slika(siguran_naziv):
        raise ValueError(
            "Dopuštene su samo PNG, JPG, JPEG i WEBP slike."
        )

    ekstenzija = siguran_naziv.rsplit(".", 1)[1].lower()

    # Generiramo jedinstveno ime kako se slike ne bi prepisivale
    novi_naziv = f"{secrets.token_hex(12)}.{ekstenzija}"

    putanja = os.path.join(
        app.config["UPLOAD_FOLDER"],
        novi_naziv
    )

    datoteka.save(putanja)

    return novi_naziv


# Funkcija briše sliku s diska
def obrisi_sliku(naziv_datoteke):
    if not naziv_datoteke:
        return

    putanja = os.path.join(
        app.config["UPLOAD_FOLDER"],
        naziv_datoteke
    )

    if os.path.isfile(putanja):
        os.remove(putanja)


# Pretvaranje vrijednosti iz HTML forme u Boolean
def pretvori_u_boolean(vrijednost):
    return str(vrijednost).lower() in {
        "true",
        "1",
        "on",
        "da"
    }

# Funkcija sortira rezultate prema parametrima iz URL-a
def sortirani_upit(model, dozvoljena_polja, zadano_polje="id"):
    polje = request.args.get("sort", zadano_polje).lower()
    smjer = request.args.get("smjer", "asc").lower()

    stupac = dozvoljena_polja.get(
        polje,
        dozvoljena_polja[zadano_polje]
    )

    if smjer == "desc":
        return model.query.order_by(stupac.desc())

    return model.query.order_by(stupac.asc())

# Dekorator koji dopušta pristup samo prijavljenom administratoru
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            if request.path == "/admin_panel":
                return redirect(url_for("index"))
            return jsonify({"uspjeh": False, "poruka": "Nemate pristup!"}), 403
        return f(*args, **kwargs)
    return wrapper

# Početna stranica pokrenuta kao 'index.html'
@app.route("/", methods=['GET'])
def index():
    return render_template("index.html")

# Ruta za prikazivanje i sortiranje projekata
@app.route("/api/projekti", methods=["GET"])
def projekti():
    svi = sortirani_upit(
        projekt,
        {
            "id": projekt.id,
            "naziv": projekt.naziv,
            "jezik": projekt.jezik,
            "status": projekt.status
        }
    ).all()

    return jsonify([
        {
            "id": zapis.id,
            "naziv": zapis.naziv,
            "jezik": zapis.jezik,
            "opis": zapis.opis,
            "status": zapis.status,
            "link": zapis.link
        }
        for zapis in svi
    ])

# Ruta za prikazivanje i sortiranje objava
@app.route("/api/objave", methods=["GET"])
def objave_prikaz():
    svi = objava.query.order_by(objava.datum_objave.desc()).all()
    return jsonify([
        {
            "id": z.id,
            "naziv": z.naziv,
            "tekst": z.tekst,
            "datum":z.datum_objave.strftime("%d.%m.%Y."),
            "slika": (
                url_for(
                    "static",
                    filename=f"uploads/{z.slika}"
                )
                if z.slika
                else None
            )
        }
        for z in svi
    ])

# Galerija stranica koja se pokreče kao galery.html
@app.route("/gallery", methods=['GET'])
def galerija():
    return render_template("galery.html")

# Ruta za prikazivanje i sortiranje slika
# Ruta za prikazivanje i sortiranje slika
@app.route("/api/slike", methods=["GET"])
def galerija_pokazi():
    svi = sortirani_upit(
        slika,
        {
            "id": slika.id,
            "slika": slika.slika,
            "u_carouselu": slika.u_carouselu,
            "projekt_id": slika.projekt_id
        }
    ).all()

    return jsonify([
        {
            "id": zapis.id,
            "slika": (
                url_for(
                    "static",
                    filename=f"uploads/{zapis.slika}"
                )
                if zapis.slika
                else None
            ),
            "u_carouselu": zapis.u_carouselu,
            "projekt_id": zapis.projekt_id,
            "projekt_naziv": zapis.projekt.naziv
        }
        for zapis in svi
    ])

# Ruta za dodavanje slike u galeriju
@app.route("/admin/slike/dodavanje", methods=["POST"])
@admin_required
def dodavanje_slike():
    datoteka = request.files.get("slika")
    projekt_id = request.form.get("projekt_id", type=int)

    if datoteka is None or datoteka.filename == "":
        return jsonify({
            "uspjeh": False,
            "poruka": "Potrebno je odabrati sliku!"
        }), 400

    if not projekt_id:
        return jsonify({
            "uspjeh": False,
            "poruka": "Potrebno je odabrati projekt!"
        }), 400

    odabrani_projekt = db.session.get(projekt, projekt_id)

    if odabrani_projekt is None:
        return jsonify({
            "uspjeh": False,
            "poruka": "Odabrani projekt ne postoji!"
        }), 404

    try:
        naziv_slike = spremi_sliku(datoteka)

    except ValueError as greska:
        return jsonify({
            "uspjeh": False,
            "poruka": str(greska)
        }), 400

    u_carouselu = pretvori_u_boolean(
        request.form.get("u_carouselu", False)
    )

    nova_slika = slika(
        slika=naziv_slike,
        u_carouselu=u_carouselu,
        projekt_id=projekt_id
    )

    db.session.add(nova_slika)
    db.session.commit()

    return jsonify({
        "uspjeh": True,
        "poruka": "Slika je uspješno dodana u galeriju!"
    }), 201

# Ruta za uređivanje slike
@app.route("/admin/slike/uredi/<int:id>", methods=["PUT"])
@admin_required
def uredivanje_slike(id):
    zapis = slika.query.get_or_404(id)

    nova_datoteka = request.files.get("slika")

    if nova_datoteka and nova_datoteka.filename:
        try:
            novi_naziv = spremi_sliku(nova_datoteka)
        except ValueError as greska:
            return jsonify({
                "uspjeh": False,
                "poruka": str(greska)
            }), 400

        obrisi_sliku(zapis.slika)
        zapis.slika = novi_naziv

    if "u_carouselu" in request.form:
        zapis.u_carouselu = pretvori_u_boolean(
            request.form.get("u_carouselu")
        )

    db.session.commit()

    return jsonify({
        "uspjeh": True,
        "poruka": "Slika je uspješno ažurirana!"
    }), 200

# Ruta za uklanjanje slike iz galerije
@app.route("/admin/slike/uklanjanje/<int:id>", methods=["DELETE"])
@admin_required
def uklanjanje_slike(id):
    zapis = slika.query.get_or_404(id)

    obrisi_sliku(zapis.slika)

    db.session.delete(zapis)
    db.session.commit()

    return jsonify({
        "uspjeh": True,
        "poruka": "Slika je uspješno uklonjena iz galerije!"
    }), 200

# Ruta za unos passworda za ulazak unutar admin panela
@app.route("/api/admin/login", methods=['POST'])
def admin_login():
    podaci = request.get_json() or {}
    if podaci and podaci.get('kod') == ADMIN_KOD:
        session['admin'] = True
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401

# Admin panel stranica koja se pokreče kao admin.html
@app.route("/admin_panel", methods=['GET'])
@admin_required
def admin_panel():
    return render_template("admin.html")

@app.route("/api/admin/logout", methods=['GET'])
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

# ruta za dodavanje projekta
@app.route("/admin/dodavanje", methods=["POST"])
@admin_required
def dodavanje_projekta():
    podaci = request.get_json() or {}
    naziv = podaci.get("naziv", "").strip()
    jezik = podaci.get('jezik', "").strip()
    opis = podaci.get('opis', "").strip()
    status = podaci.get('status', "").strip()
    link = podaci.get('link', "").strip()

    if not naziv or not jezik or not opis or not status or not link:
        return jsonify({
            "uspjeh": False,
            "poruka": "Naziv, jezik, opis, status i link su obavezni podaci!"
        }), 400

    if projekt.query.filter_by(naziv=naziv).first():
        return jsonify({
            "uspjeh": False,
            "poruka": "Projekt s tim nazivom već postoji!"
        }), 400
    
    novi = projekt(naziv=naziv, jezik=jezik, opis=opis, status=status, link=link)
    db.session.add(novi)
    db.session.commit()
    return jsonify({'uspjeh': True, 'poruka': 'Projekt je uspješno dodan!'}), 201

# ruta za uklanjanje projekta
@app.route("/admin/uklanjanje/<int:id>", methods=["DELETE"])
@admin_required
def uklanjanje_projekta(id):
    zapis = projekt.query.get_or_404(id)

    for povezana_slika in zapis.slike:
        obrisi_sliku(povezana_slika.slika)

    db.session.delete(zapis)
    db.session.commit()

    return jsonify({
        "uspjeh": True,
        "poruka": "Projekt je uspješno uklonjen!"
    }), 200

# ruta za uređivanje informacija o projektu
@app.route('/admin/uredi/<int:id>', methods=['PUT'])
@admin_required
def uredivanje_projekta(id):
    zapis= projekt.query.get_or_404(id)
    podaci = request.get_json() or {}
    naziv = podaci.get('naziv', "").strip()
    jezik = podaci.get('jezik', "").strip()
    opis = podaci.get('opis', "").strip()
    status = podaci.get('status', "").strip()
    link = podaci.get('link', "").strip()

    if not naziv or not jezik or not opis or not status or not link:
        return jsonify({
            "uspjeh": False,
            "poruka": "Naziv, jezik, opis, status i link su obavezni podaci!"
        }), 400
    
    postojeci_projekt = projekt.query.filter(
    projekt.naziv == naziv,
    projekt.id != id
    ).first()

    if postojeci_projekt:
        return jsonify({
            "uspjeh": False,
            "poruka": "Drugi projekt s tim nazivom već postoji!"
        }), 400
     
    zapis.naziv = naziv
    zapis.jezik = jezik
    zapis.opis = opis
    zapis.status = status
    zapis.link = link

    db.session.commit()
    return jsonify({'uspjeh': True, 'poruka': 'Projekt je uspješno ažuriran!'}), 200

# Ruta za dodavanje objave
@app.route("/admin/objave/dodavanje", methods=["POST"])
@admin_required
def dodavanje_objave():
    naziv = request.form.get("naziv", "").strip()
    tekst = request.form.get("tekst", "").strip()

    if not naziv or not tekst:
        return jsonify({
            "uspjeh": False,
            "poruka": "Naziv i tekst objave obavezni su podaci!"
        }), 400

    if objava.query.filter_by(naziv=naziv).first():
        return jsonify({
            "uspjeh": False,
            "poruka": "Objava s tim nazivom već postoji!"
        }), 400

    try:
        naziv_slike = spremi_sliku(
            request.files.get("slika")
        )
    except ValueError as greska:
        return jsonify({
            "uspjeh": False,
            "poruka": str(greska)
        }), 400

    nova_objava = objava(
        naziv=naziv,
        tekst=tekst,
        slika=naziv_slike
    )

    db.session.add(nova_objava)
    db.session.commit()

    return jsonify({
        "uspjeh": True,
        "poruka": "Objava je uspješno dodana!"
    }), 201

# Ruta za uređivanje objave
@app.route("/admin/objave/uredi/<int:id>", methods=["PUT"])
@admin_required
def uredivanje_objave(id):
    zapis = objava.query.get_or_404(id)

    naziv = request.form.get("naziv", "").strip()
    tekst = request.form.get("tekst", "").strip()

    if not naziv or not tekst:
        return jsonify({
            "uspjeh": False,
            "poruka": "Naziv i tekst objave obavezni su podaci!"
        }), 400

    postojeca_objava = objava.query.filter(
        objava.naziv == naziv,
        objava.id != id
    ).first()

    if postojeca_objava:
        return jsonify({
            "uspjeh": False,
            "poruka": "Druga objava s tim nazivom već postoji!"
        }), 400

    nova_slika = request.files.get("slika")
    treba_obrisati_sliku = pretvori_u_boolean(
        request.form.get("obrisi_sliku", False)
    )

    if nova_slika and nova_slika.filename:
        try:
            novi_naziv_slike = spremi_sliku(nova_slika)
        except ValueError as greska:
            return jsonify({
                "uspjeh": False,
                "poruka": str(greska)
            }), 400

        obrisi_sliku(zapis.slika)
        zapis.slika = novi_naziv_slike

    elif treba_obrisati_sliku:
        obrisi_sliku(zapis.slika)
        zapis.slika = None

    zapis.naziv = naziv
    zapis.tekst = tekst

    db.session.commit()

    return jsonify({
        "uspjeh": True,
        "poruka": "Objava je uspješno ažurirana!"
    }), 200

# Ruta za uklanjanje objave
@app.route("/admin/objave/uklanjanje/<int:id>", methods=["DELETE"])
@admin_required
def uklanjanje_objave(id):
    zapis = objava.query.get_or_404(id)

    obrisi_sliku(zapis.slika)

    db.session.delete(zapis)
    db.session.commit()

    return jsonify({
        "uspjeh": True,
        "poruka": "Objava je uspješno uklonjena!"
    }), 200

# Ruta za prikazivanje about me stranice
@app.route("/about", methods=['GET'])
def about():
    return render_template("about.html")

# Pokretanje aplikacijskog programskog koda te definiranje da se pokrene sa debug-om po domačinu '0.0.0.0' na portu '8080'
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
