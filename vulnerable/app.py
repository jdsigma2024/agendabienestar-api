"""
AgendaBienestar UNIMINUTO - API de citas de Bienestar Universitario
=====================================================================
VERSION VULNERABLE: escrita con fallas INTENCIONALES para la actividad de
Desarrollo de Software Seguro (Unidad 2). Usela solo en su equipo (localhost).

Ejecutar:  python app.py      ->  http://127.0.0.1:5000
"""
import base64
import hashlib
import json
import os
import sqlite3
import sys
from datetime import date, timedelta

from flask import Flask, g, jsonify, request

# Pantallas web (Jinja2) y documentacion OpenAPI compartidas: carpeta ../web
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from web.paginas import web  # noqa: E402

app = Flask(__name__)
app.config["VERSION_NOMBRE"] = "0.9 (con fallas intencionales)"
app.register_blueprint(web)

SECRET_KEY = "bienestar2026"  # clave de la aplicacion
DB = os.environ.get("BIENESTAR_DB", "bienestar.db")


# --------------------------------------------------------------------------
# Base de datos
# --------------------------------------------------------------------------
def conectar():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def cerrar(_):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def md5(texto):
    return hashlib.md5(texto.encode()).hexdigest()


def init_db():
    con = sqlite3.connect(DB)
    con.executescript("""
        DROP TABLE IF EXISTS usuarios;
        DROP TABLE IF EXISTS citas;
        CREATE TABLE usuarios (id INTEGER PRIMARY KEY, correo TEXT UNIQUE, nombre TEXT,
                               clave TEXT, rol TEXT);
        CREATE TABLE citas (id INTEGER PRIMARY KEY, estudiante_id INTEGER, profesional_id INTEGER,
                            fecha TEXT, servicio TEXT, motivo TEXT, notas TEXT, estado TEXT);
    """)
    usuarios = [
        (1, "ana@uniminuto.edu.co", "Ana Rojas", md5("Ana2026*"), "estudiante"),
        (2, "carlos@uniminuto.edu.co", "Carlos Pérez", md5("Carlos2026*"), "estudiante"),
        (3, "laura.psico@uniminuto.edu.co", "Laura Gómez", md5("Psico2026*"), "profesional"),
        (4, "admin.bienestar@uniminuto.edu.co", "Administrador", md5("Admin2026*"), "admin"),
    ]
    con.executemany("INSERT INTO usuarios VALUES (?,?,?,?,?)", usuarios)
    hoy = date.today()
    citas = [
        (1, 1, 3, str(hoy + timedelta(days=1)), "Psicología", "Ansiedad antes de parciales",
         "Seguimiento por estrés académico. Sugerir técnicas de respiración.", "programada"),
        (2, 2, 3, str(hoy + timedelta(days=2)), "Psicología", "Dificultades familiares",
         "Primera sesión. Remitir a orientación familiar si persiste.", "programada"),
        (3, 1, 3, str(hoy - timedelta(days=5)), "Asesoría académica", "Plan de estudio",
         "Se acordó un horario semanal de estudio.", "atendida"),
    ]
    con.executemany("INSERT INTO citas VALUES (?,?,?,?,?,?,?,?)", citas)
    con.commit()
    con.close()


# --------------------------------------------------------------------------
# Autenticacion
# --------------------------------------------------------------------------
def emitir_token(usuario):
    datos = {"id": usuario["id"], "rol": usuario["rol"]}
    return base64.urlsafe_b64encode(json.dumps(datos).encode()).decode()


def usuario_actual():
    cabecera = request.headers.get("Authorization", "")
    if not cabecera.startswith("Bearer "):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(cabecera[7:]))
    except Exception:
        return None


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@app.post("/api/registro")
def registro():
    datos = request.get_json(force=True)
    con = conectar()
    con.execute(
        "INSERT INTO usuarios (correo, nombre, clave, rol) VALUES (?,?,?,?)",
        (datos["correo"], datos.get("nombre", ""), md5(datos["clave"]), datos.get("rol", "estudiante")),
    )
    con.commit()
    return jsonify({"mensaje": "Usuario creado"}), 201


@app.post("/api/login")
def login():
    datos = request.get_json(force=True)
    u = conectar().execute("SELECT * FROM usuarios WHERE correo = ?", (datos.get("correo"),)).fetchone()
    if u is None:
        return jsonify({"error": "El correo no está registrado"}), 404
    if u["clave"] != md5(datos.get("clave", "")):
        return jsonify({"error": "Contraseña incorrecta"}), 401
    return jsonify({"token": emitir_token(u), "rol": u["rol"]})


@app.get("/api/mis-citas")
def mis_citas():
    u = usuario_actual()
    if not u:
        return jsonify({"error": "No autenticado"}), 401
    if u.get("rol") == "profesional":
        filas = conectar().execute("SELECT * FROM citas WHERE profesional_id = ?", (u["id"],)).fetchall()
    else:
        filas = conectar().execute("SELECT * FROM citas WHERE estudiante_id = ?", (u["id"],)).fetchall()
    return jsonify([dict(f) for f in filas])


@app.post("/api/citas")
def crear_cita():
    u = usuario_actual()
    if not u:
        return jsonify({"error": "No autenticado"}), 401
    d = request.get_json(force=True)
    con = conectar()
    cur = con.execute(
        "INSERT INTO citas (estudiante_id, profesional_id, fecha, servicio, motivo, notas, estado) "
        "VALUES (?,?,?,?,?,?,?)",
        (u["id"], d.get("profesional_id", 3), d["fecha"], d["servicio"], d.get("motivo", ""), "", "programada"),
    )
    con.commit()
    return jsonify({"id": cur.lastrowid}), 201


@app.get("/api/citas/<int:cita_id>")
def ver_cita(cita_id):
    if not usuario_actual():
        return jsonify({"error": "No autenticado"}), 401
    c = conectar().execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    if c is None:
        return jsonify({"error": "No existe"}), 404
    return jsonify(dict(c))


@app.patch("/api/citas/<int:cita_id>")
def modificar_cita(cita_id):
    if not usuario_actual():
        return jsonify({"error": "No autenticado"}), 401
    d = request.get_json(force=True)
    con = conectar()
    for campo, valor in d.items():
        if campo in ("fecha", "servicio", "motivo", "notas", "estado", "profesional_id", "estudiante_id"):
            con.execute(f"UPDATE citas SET {campo} = ? WHERE id = ?", (valor, cita_id))
    con.commit()
    return jsonify({"mensaje": "Cita actualizada"})


@app.get("/api/reportes/ocupacion")
def reporte_ocupacion():
    u = usuario_actual()
    if not u or u.get("rol") != "admin":
        return jsonify({"error": "Solo administradores"}), 403
    dias = int(request.args.get("dias", 30))
    citas = conectar().execute("SELECT fecha FROM citas").fetchall()
    inicio = date.today() - timedelta(days=dias)
    resultado = {}
    for i in range(dias):
        dia = str(inicio + timedelta(days=i))
        resultado[dia] = sum(1 for c in citas if c["fecha"] == dia)
    return jsonify(resultado)


@app.get("/api/diagnostico")
def diagnostico():
    return jsonify({"version": "0.9-beta", "db": DB, "secret_key": SECRET_KEY, "debug": app.debug})


# Al arrancar con gunicorn (Render) no se ejecuta el bloque __main__: se crea la base aqui.
# En Render el disco es efimero: la base vuelve a su estado inicial en cada reinicio.
if os.environ.get("BIENESTAR_AUTO_INIT", "1") == "1" and not os.path.exists(DB):
    init_db()


if __name__ == "__main__":
    if not os.path.exists(DB):
        init_db()
    app.run(debug=True)
