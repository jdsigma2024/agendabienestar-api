"""
Pruebas de regresion de seguridad de AgendaBienestar.

Cada prueba verifica que una amenaza del modelo STRIDE esta MITIGADA.
- Contra la carpeta 'vulnerable' deben FALLAR (rojo): demuestran el hallazgo.
- Contra la version corregida deben PASAR (verde): demuestran la correccion.
Las pruebas "funcionales" deben pasar siempre: la correccion no puede romper la app.
"""
import base64
import hashlib
import json
import sqlite3
import time

from conftest import ADMIN, ANA, CARLOS, LAURA


def token_falso(datos):
    return {"Authorization": "Bearer " + base64.urlsafe_b64encode(json.dumps(datos).encode()).decode()}


# ---------------------------------------------------------------- funcionales
def test_funcional_login_y_mis_citas(cliente, token):
    r = cliente.get("/api/mis-citas", headers=token(*ANA))
    assert r.status_code == 200
    assert {c["id"] for c in r.get_json()} == {1, 3}


def test_funcional_estudiante_ve_y_cancela_su_cita(cliente, token):
    h = token(*ANA)
    assert cliente.get("/api/citas/1", headers=h).status_code == 200
    assert cliente.patch("/api/citas/1", json={"estado": "cancelada"}, headers=h).status_code == 200


def test_funcional_profesional_registra_notas(cliente, token):
    h = token(*LAURA)
    r = cliente.patch("/api/citas/1", json={"notas": "Evolución favorable."}, headers=h)
    assert r.status_code == 200


def test_funcional_admin_ve_reporte(cliente, token):
    r = cliente.get("/api/reportes/ocupacion?dias=30", headers=token(*ADMIN))
    assert r.status_code == 200


def test_funcional_pantallas_web(cliente):
    for ruta in ("/", "/registro", "/citas", "/citas/1", "/reporte", "/docs"):
        r = cliente.get(ruta)
        assert r.status_code == 200, ruta
        assert r.mimetype == "text/html"
    assert cliente.get("/web-static/app.js").status_code == 200


def test_funcional_openapi(cliente, modulo):
    r = cliente.get("/openapi.json")
    assert r.status_code == 200
    spec = r.get_json()
    assert spec["openapi"].startswith("3.")
    reglas = {str(x.rule).replace("<int:cita_id>", "{id}") for x in modulo.app.url_map.iter_rules()}
    for ruta in spec["paths"]:
        assert ruta in reglas, f"{ruta} esta documentada pero no existe"


# ---------------------------------------------------------------- S: suplantacion
def test_H1_token_alterado_no_da_privilegios(cliente):
    """S/E - Un token fabricado por el cliente no debe aceptarse (CWE-347)."""
    r = cliente.get("/api/reportes/ocupacion", headers=token_falso({"id": 1, "rol": "admin"}))
    assert r.status_code in (401, 403)


def test_H2_login_no_revela_si_el_correo_existe(cliente):
    """S/I - Enumeracion de usuarios (CWE-204)."""
    a = cliente.post("/api/login", json={"correo": "noexiste@uniminuto.edu.co", "clave": "x"})
    b = cliente.post("/api/login", json={"correo": ANA[0], "clave": "x"})
    assert a.status_code == b.status_code
    assert a.get_json() == b.get_json()


def test_H2_limite_de_intentos(cliente):
    """S - Fuerza bruta sin limite de intentos (CWE-307)."""
    codigos = [cliente.post("/api/login", json={"correo": ANA[0], "clave": f"mala{i}"}).status_code
               for i in range(6)]
    assert codigos[-1] == 429


# ---------------------------------------------------------------- T: manipulacion
def test_H9_estudiante_no_modifica_cita_ajena(cliente, token):
    """T - Ana no puede cancelar la cita de Carlos (CWE-639)."""
    r = cliente.patch("/api/citas/2", json={"estado": "cancelada"}, headers=token(*ANA))
    assert r.status_code in (403, 404)


def test_H9_estudiante_no_cambia_campos_protegidos(cliente, token):
    """T - Asignacion masiva: el estudiante no escribe notas ni marca 'atendida' (CWE-915)."""
    h = token(*ANA)
    assert cliente.patch("/api/citas/1", json={"notas": "inventado"}, headers=h).status_code in (400, 403)
    assert cliente.patch("/api/citas/1", json={"estado": "atendida"}, headers=h).status_code in (400, 403)


# ---------------------------------------------------------------- R: repudio
def test_H7_queda_registro_de_auditoria(cliente, token, modulo):
    """R - Debe quedar evidencia de quien intento ver una cita (CWE-778)."""
    cliente.get("/api/citas/1", headers=token(*CARLOS))
    con = sqlite3.connect(modulo.DB)
    try:
        filas = con.execute("SELECT usuario_id, recurso FROM auditoria WHERE recurso = 'cita:1'").fetchall()
    except sqlite3.OperationalError:
        filas = []
    con.close()
    assert (2, "cita:1") in filas


# ---------------------------------------------------------------- I: divulgacion
def test_H4_estudiante_no_ve_cita_ajena(cliente, token):
    """I - IDOR / BOLA: Carlos no puede leer la cita (ni las notas) de Ana (CWE-639)."""
    r = cliente.get("/api/citas/1", headers=token(*CARLOS))
    assert r.status_code in (403, 404)
    assert "notas" not in (r.get_json() or {})


def test_H4_estudiante_no_ve_notas_clinicas_propias(cliente, token):
    """I - Minimizacion de datos (Ley 1581): las notas son del profesional."""
    r = cliente.get("/api/citas/1", headers=token(*ANA))
    assert "notas" not in r.get_json()


def test_H5_claves_no_se_guardan_en_md5(cliente, modulo):
    """I - Hash debil sin sal (CWE-328 / CWE-916)."""
    con = sqlite3.connect(modulo.DB)
    clave = con.execute("SELECT clave FROM usuarios WHERE id = 1").fetchone()[0]
    con.close()
    assert clave != hashlib.md5(ANA[1].encode()).hexdigest()


def test_H6_no_se_exponen_secretos(cliente):
    """I - Endpoint de diagnostico expone la clave de firma (CWE-215 / CWE-798)."""
    r = cliente.get("/api/diagnostico")
    assert r.status_code == 404 or "secret_key" not in (r.get_json() or {})


def test_cabeceras_de_seguridad(cliente):
    """I - Lo que un DAST como ZAP reporta como 'cabecera ausente'."""
    r = cliente.post("/api/login", json={"correo": ANA[0], "clave": ANA[1]})
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


# ---------------------------------------------------------------- D: denegacion de servicio
def test_H8_reporte_rechaza_rangos_enormes(cliente, token):
    """D - Consumo de recursos sin limite (CWE-770)."""
    h = token(*ADMIN)
    inicio = time.perf_counter()
    r = cliente.get("/api/reportes/ocupacion?dias=200000", headers=h)
    assert r.status_code == 400
    assert time.perf_counter() - inicio < 1


# ---------------------------------------------------------------- E: elevacion de privilegios
def test_H3_registro_no_permite_elegir_rol(cliente):
    """E - Asignacion masiva en el registro (CWE-915)."""
    datos = {"correo": "eva@uniminuto.edu.co", "nombre": "Eva", "clave": "ClaveSegura2026*", "rol": "admin"}
    cliente.post("/api/registro", json=datos)
    r = cliente.post("/api/login", json={"correo": datos["correo"], "clave": datos["clave"]})
    assert r.status_code == 200
    assert r.get_json()["rol"] == "estudiante"


def test_H1_estudiante_no_accede_a_reportes(cliente, token):
    """E - Un estudiante autentico no puede usar funciones de administrador."""
    r = cliente.get("/api/reportes/ocupacion", headers=token(*ANA))
    assert r.status_code == 403
