# AgendaBienestar UNIMINUTO — API de práctica de seguridad
## Desarrollo de Software Seguro
### Profesor: José Sánchez

API en Python (Flask) para agendar citas de Bienestar Universitario: psicología, asesoría académica y salud.
Se usa en la actividad **"Modelado de amenazas y pentesting de caja gris de AgendaBienestar"** de
*Desarrollo de Software Seguro* (Unidad 2).

> **Aviso ético y legal.** La carpeta `vulnerable/` contiene fallas **intencionales**. Ejecútela solo
> en su propio equipo (`localhost`). Atacar sistemas de terceros sin autorización escrita es un delito
> (en Colombia, Ley 1273 de 2009). Los datos de la base son ficticios.

## Estructura

```
agendabienestar-api/
├── vulnerable/app.py            API con 9 hallazgos intencionales (H1 a H9)
├── seguro/app.py                versión corregida: la crea el equipo en la Parte 6
                                 (en el paquete del docente viene la solución)
├── tests/
│   ├── conftest.py              carga la versión indicada en la variable APP
│   └── test_seguridad.py        pruebas de regresión de seguridad, una o más por amenaza
├── web/                         pantallas y documentación (compartidas por las dos versiones)
│   ├── paginas.py               rutas de las pantallas, /docs y /openapi.json
│   ├── templates/               plantillas Jinja2
│   ├── static/                  estilos.css (Tailwind ya compilado) y JavaScript
│   ├── tailwind/entrada.css     fuente de los estilos (Tailwind CSS v4)
│   └── openapi.json             especificación OpenAPI 3
├── k6/estres.js                 prueba de estrés del reporte de ocupación
├── requirements.txt             dependencias actuales
├── requirements-auditoria.txt   dependencias antiguas para el ejercicio de SCA (no instalar)
└── .github/workflows/devsecops.yml   pipeline: secretos, SAST, SCA y pruebas
```

## Puesta en marcha

```bash
python -m venv venv
# Windows: venv\Scripts\activate      Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cd vulnerable
python app.py            # crea bienestar.db y queda en http://127.0.0.1:5000
```

## Despliegue en Render (opcional)

1. Suba esta carpeta a un repositorio de GitHub.
2. En Render: **New → Blueprint**, elija el repositorio. Render lee `render.yaml` y crea el servicio
   `agendabienestar-vulnerable` en el plan gratuito.
   (Sin Blueprint: **New → Web Service**, Build `pip install -r requirements.txt`,
   Start `gunicorn --chdir vulnerable app:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT`.)
3. En todos los comandos de la guía, reemplace `http://127.0.0.1:5000` por la URL del servicio,
   por ejemplo `https://agendabienestar-vulnerable.onrender.com`.

Tenga en cuenta:

- **La base de datos se reinicia sola.** El disco del plan gratuito es efímero: la base SQLite vuelve
  al estado inicial cuando el servicio se reinicia, se vuelve a desplegar o se duerme. Para limpiar
  la base entre grupos, use **Manual Deploy → Deploy latest commit** o **Restart service**.
- **Se duerme a los 15 minutos sin tráfico** y tarda cerca de un minuto en despertar. Abra la URL
  unos minutos antes de la clase.
- **Un servicio por equipo.** Si todos atacan la misma instancia, los cambios de un equipo
  (citas canceladas, cuentas nuevas) afectan a los demás. Lo ideal es que cada equipo despliegue
  su propio servicio desde su repositorio.
- **Use `--workers 1`.** SQLite y el límite de intentos viven en memoria de un solo proceso.
- **No ejecute `python app.py` en Render:** la versión vulnerable activa el modo debug de Flask,
  que en un servidor público permitiría ejecutar código.
- **La prueba de estrés (k6) se hace solo en localhost.** Una instancia gratuita tiene muy poca CPU
  y la infraestructura es compartida con otros clientes de Render.
- **Es una aplicación vulnerable en Internet.** Los datos son ficticios, pero suspenda el servicio
  (**Settings → Suspend**) al terminar la actividad.

## Pantallas web y Swagger UI

Con la API en marcha, abra el navegador:

| Dirección | Qué es |
|-----------|--------|
| http://127.0.0.1:5000/ | Inicio de sesión |
| http://127.0.0.1:5000/registro | Crear cuenta |
| http://127.0.0.1:5000/citas | Mis citas y solicitar cita |
| http://127.0.0.1:5000/citas/2 | Detalle de una cita (cancelar, notas del profesional) |
| http://127.0.0.1:5000/reporte | Reporte de ocupación (administrador) |
| http://127.0.0.1:5000/docs | **Swagger UI**: probar cada servicio sin curl ni Postman |
| http://127.0.0.1:5000/openapi.json | Especificación OpenAPI 3 |

- Las pantallas (plantillas Jinja2 en `web/templates`) **no tocan la base de datos**: llaman a la API
  con `fetch()`. Abra **F12 → Red** para ver cada petición, su token y su respuesta.
- **Swagger UI:** ejecute `POST /api/login` con *Try it out*, copie el `token`, pulse **Authorize**
  y péguelo. Desde ese momento todas las peticiones llevan `Authorization: Bearer …`.
- El diseño usa **Tailwind CSS v4**. El archivo `web/static/estilos.css` ya viene compilado, así que
  no hace falta Node.js para ejecutar la aplicación. Solo si cambia clases en las plantillas o en
  `app.js`, vuelva a compilarlo:
  `npx @tailwindcss/cli -i web/tailwind/entrada.css -o web/static/estilos.css --minify`
- Swagger UI se carga desde un CDN (jsDelivr), así que el navegador necesita Internet. Sin conexión,
  `/openapi.json` sigue disponible y se puede importar en Postman o Insomnia.
- La especificación describe lo que el equipo **dice** que hace la API. En la prueba de caja gris,
  compárela con el código: hay rutas y campos que no están documentados.

## Usuarios de prueba

| Rol          | Correo                              | Clave        |
|--------------|-------------------------------------|--------------|
| Estudiante   | ana@uniminuto.edu.co                | Ana2026*     |
| Estudiante   | carlos@uniminuto.edu.co             | Carlos2026*  |
| Profesional  | laura.psico@uniminuto.edu.co        | Psico2026*   |
| Administrador| admin.bienestar@uniminuto.edu.co    | Admin2026*   |

La prueba es de **caja gris**: el equipo recibe la cuenta de Carlos y el código fuente,
pero no las demás claves.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST  | `/api/registro` | Crear cuenta |
| POST  | `/api/login` | Iniciar sesión; devuelve un token |
| GET   | `/api/mis-citas` | Citas del usuario autenticado |
| POST  | `/api/citas` | Solicitar una cita |
| GET   | `/api/citas/{id}` | Ver una cita |
| PATCH | `/api/citas/{id}` | Modificar una cita (cancelar, registrar notas) |
| GET   | `/api/reportes/ocupacion?dias=N` | Reporte de ocupación (administrador) |
| GET   | `/api/diagnostico` | Información técnica del servicio |

Ejemplo con curl:

```bash
curl -s -X POST http://127.0.0.1:5000/api/login -H "Content-Type: application/json" \
     -d '{"correo":"carlos@uniminuto.edu.co","clave":"Carlos2026*"}'
curl -s http://127.0.0.1:5000/api/mis-citas -H "Authorization: Bearer <token>"
```

## Pruebas de regresión de seguridad

```bash
pytest -v                    # prueba la carpeta vulnerable: deben fallar 13 de 20 pruebas
APP=seguro pytest -v         # prueba su versión corregida: deben pasar las 20
# Windows PowerShell:  $env:APP="seguro"; pytest -v
```

Las pruebas `test_funcional_*` deben pasar siempre: una corrección de seguridad no puede romper la aplicación.

## Herramientas de la actividad

```bash
pip install bandit pip-audit
bandit -r vulnerable                                              # SAST
pip-audit -r requirements-auditoria.txt --no-deps --disable-pip   # SCA
k6 run -e TOKEN="<token admin>" -e DIAS=50000 k6/estres.js         # estrés (requiere k6)
docker run --rm -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://host.docker.internal:5000/api/diagnostico  # DAST
```

`gitleaks` (escaneo de secretos) se ejecuta en el pipeline de GitHub Actions; también puede instalarse localmente.
