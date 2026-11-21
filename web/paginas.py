"""
Pantallas web (Jinja2) y documentacion OpenAPI de AgendaBienestar.

Las pantallas NO acceden a la base de datos: son paginas que llaman a la misma API
REST con fetch() desde el navegador. Por eso cualquier falla de la API tambien se
puede observar desde aqui, en la pestana "Red" (Network) de las herramientas del
navegador (F12).

Rutas:
    /                   Inicio de sesion
    /registro           Crear cuenta
    /citas              Mis citas y solicitar cita
    /citas/<id>         Detalle de una cita
    /reporte            Reporte de ocupacion (administrador)
    /docs               Swagger UI para probar la API
    /openapi.json       Especificacion OpenAPI 3
"""
import os

from flask import Blueprint, current_app, render_template, send_from_directory

CARPETA = os.path.dirname(os.path.abspath(__file__))

web = Blueprint("web", __name__, template_folder="templates",
                static_folder="static", static_url_path="/web-static")


@web.app_context_processor
def datos_comunes():
    return {"version": current_app.config.get("VERSION_NOMBRE", "")}


@web.get("/")
def inicio():
    return render_template("login.html", titulo="Iniciar sesión")


@web.get("/registro")
def registro():
    return render_template("registro.html", titulo="Crear cuenta")


@web.get("/citas")
def citas():
    return render_template("citas.html", titulo="Mis citas")


@web.get("/citas/<int:cita_id>")
def detalle(cita_id):
    return render_template("detalle.html", titulo=f"Cita {cita_id}", cita_id=cita_id)


@web.get("/reporte")
def reporte():
    return render_template("reporte.html", titulo="Reporte de ocupación")


@web.get("/docs")
def docs():
    return render_template("docs.html", titulo="API · Swagger UI")


@web.get("/openapi.json")
def openapi():
    return send_from_directory(CARPETA, "openapi.json", mimetype="application/json")
