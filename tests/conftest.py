"""
Configuracion de las pruebas.

Por defecto se prueba la carpeta 'vulnerable'. Para probar otra version:
    APP=seguro pytest -v          (Linux / macOS)
    set APP=seguro && pytest -v   (Windows cmd)
    $env:APP="seguro"; pytest -v  (PowerShell)
"""
import importlib.util
import os
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
os.environ["BIENESTAR_AUTO_INIT"] = "0"  # cada prueba crea su propia base temporal


def cargar_app(carpeta):
    ruta = RAIZ / carpeta / "app.py"
    spec = importlib.util.spec_from_file_location(f"app_{carpeta}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def modulo(tmp_path):
    m = cargar_app(os.environ.get("APP", "vulnerable"))
    m.DB = str(tmp_path / "prueba.db")
    m.init_db()
    if hasattr(m, "_fallidos"):
        m._fallidos.clear()
    m.app.config["TESTING"] = True
    return m


@pytest.fixture
def cliente(modulo):
    return modulo.app.test_client()


@pytest.fixture
def token(cliente):
    def _token(correo, clave):
        r = cliente.post("/api/login", json={"correo": correo, "clave": clave})
        assert r.status_code == 200, r.get_json()
        return {"Authorization": "Bearer " + r.get_json()["token"]}
    return _token


ANA = ("ana@uniminuto.edu.co", "Ana2026*")
CARLOS = ("carlos@uniminuto.edu.co", "Carlos2026*")
LAURA = ("laura.psico@uniminuto.edu.co", "Psico2026*")
ADMIN = ("admin.bienestar@uniminuto.edu.co", "Admin2026*")
