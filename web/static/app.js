// AgendaBienestar UNIMINUTO - logica de las pantallas.
// Cada pantalla llama a la API REST con fetch(). Abra F12 > Red para ver las peticiones.
// Los datos se pintan siempre con textContent (nunca con innerHTML) para no abrir XSS.
"use strict";

const sesion = {
  get token() { return sessionStorage.getItem("token"); },
  get rol() { return sessionStorage.getItem("rol"); },
  get correo() { return sessionStorage.getItem("correo"); },
  guardar(token, rol, correo) {
    sessionStorage.setItem("token", token);
    sessionStorage.setItem("rol", rol);
    sessionStorage.setItem("correo", correo);
  },
  cerrar() { sessionStorage.clear(); },
};

async function api(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, headers: {} };
  if (sesion.token) opciones.headers["Authorization"] = "Bearer " + sesion.token;
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }
  const resp = await fetch(ruta, opciones);
  let datos = null;
  try { datos = await resp.json(); } catch (e) { datos = null; }
  return { ok: resp.ok, estado: resp.status, datos };
}

function mostrar(texto, tipo) {
  const caja = document.getElementById("mensaje");
  caja.textContent = texto;
  caja.className = "mensaje mensaje-" + (tipo || "info");
  caja.hidden = false;
}

function mostrarError(r) {
  const detalle = r.datos && r.datos.error ? r.datos.error : "Error inesperado";
  mostrar(`HTTP ${r.estado}: ${detalle}`, "error");
}

function celda(fila, texto) {
  const td = document.createElement("td");
  td.textContent = texto === null || texto === undefined ? "" : String(texto);
  fila.appendChild(td);
  return td;
}

function insignia(estado) {
  const s = document.createElement("span");
  const conocido = ["programada", "atendida", "cancelada"].includes(estado);
  s.className = "insignia insignia-" + (conocido ? estado : "cancelada");
  s.textContent = estado === null || estado === undefined ? "—" : String(estado);
  return s;
}

function filaVacia(cuerpo, columnas, texto) {
  cuerpo.replaceChildren();
  const tr = document.createElement("tr");
  const td = celda(tr, texto);
  td.colSpan = columnas;
  td.className = "text-slate-500";
  cuerpo.appendChild(tr);
}

function exigirSesion() {
  if (!sesion.token) { window.location.href = "/"; return false; }
  return true;
}

// Muestra u oculta los elementos marcados con data-requiere="sesion|estudiante|profesional|admin".
function ajustarNavegacion() {
  document.querySelectorAll("[data-requiere]").forEach((el) => {
    const req = el.dataset.requiere;
    const visible = req === "sesion" ? !!sesion.token : sesion.rol === req;
    el.hidden = !visible;
  });
  const usuario = document.getElementById("usuario");
  if (sesion.token) {
    document.getElementById("usuario-inicial").textContent = (sesion.correo || "?").charAt(0).toUpperCase();
    document.getElementById("usuario-correo").textContent = sesion.correo;
    document.getElementById("usuario-rol").textContent = sesion.rol;
    usuario.hidden = false;
  }
  const actual = document.body.dataset.pagina === "detalle" ? "citas" : document.body.dataset.pagina;
  document.querySelectorAll("[data-nav]").forEach((a) => {
    if (a.dataset.nav === actual) { a.classList.add("nav-activo"); a.setAttribute("aria-current", "page"); }
  });
  document.getElementById("salir").addEventListener("click", () => {
    sesion.cerrar();
    window.location.href = "/";
  });
}

const paginas = {
  login() {
    if (sesion.token) { window.location.href = "/citas"; return; }
    document.getElementById("form-login").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const correo = ev.target.correo.value.trim();
      const r = await api("POST", "/api/login", { correo, clave: ev.target.clave.value });
      if (!r.ok) return mostrarError(r);
      sesion.guardar(r.datos.token, r.datos.rol, correo);
      window.location.href = r.datos.rol === "admin" ? "/reporte" : "/citas";
    });
  },

  registro() {
    document.getElementById("form-registro").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const f = ev.target;
      const r = await api("POST", "/api/registro",
        { nombre: f.nombre.value, correo: f.correo.value.trim(), clave: f.clave.value });
      if (!r.ok) return mostrarError(r);
      mostrar("Cuenta creada. Ya puede iniciar sesión.", "exito");
      f.reset();
    });
  },

  async citas() {
    if (!exigirSesion()) return;
    const cuerpo = document.getElementById("lista-citas");
    const cargar = async () => {
      const r = await api("GET", "/api/mis-citas");
      if (!r.ok) { filaVacia(cuerpo, 6, "No fue posible cargar las citas."); return mostrarError(r); }
      ["programada", "atendida", "cancelada"].forEach((e) => {
        document.getElementById("total-" + e).textContent = r.datos.filter((c) => c.estado === e).length;
      });
      if (r.datos.length === 0) return filaVacia(cuerpo, 6, "Aún no tienes citas.");
      cuerpo.replaceChildren();
      r.datos.forEach((c) => {
        const tr = document.createElement("tr");
        celda(tr, c.id).className = "font-semibold text-slate-500";
        celda(tr, c.fecha).className = "whitespace-nowrap font-medium";
        [c.servicio, c.motivo].forEach((v) => celda(tr, v));
        celda(tr, "").appendChild(insignia(c.estado));
        const enlace = document.createElement("a");
        enlace.href = `/citas/${encodeURIComponent(c.id)}`;
        enlace.textContent = "Ver detalle →";
        enlace.className = "font-semibold whitespace-nowrap no-underline hover:underline";
        const td = celda(tr, "");
        td.className = "text-right";
        td.appendChild(enlace);
        cuerpo.appendChild(tr);
      });
    };
    document.getElementById("form-cita").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const f = ev.target;
      const r = await api("POST", "/api/citas",
        { fecha: f.fecha.value, servicio: f.servicio.value, motivo: f.motivo.value });
      if (!r.ok) return mostrarError(r);
      mostrar(`Cita ${r.datos.id} solicitada.`, "exito");
      f.reset();
      cargar();
    });
    cargar();
  },

  async detalle() {
    if (!exigirSesion()) return;
    const id = document.getElementById("detalle").dataset.cita;
    const pintar = (c) => {
      const campos = { fecha: c.fecha, servicio: c.servicio, motivo: c.motivo || "—",
                       estudiante: c.estudiante_id, profesional: c.profesional_id };
      Object.entries(campos).forEach(([k, v]) => {
        document.getElementById("d-" + k).textContent = v === null || v === undefined ? "—" : String(v);
      });
      document.getElementById("d-estado").replaceChildren(insignia(c.estado));
      const arriba = document.getElementById("d-estado-insignia");
      arriba.replaceWith(Object.assign(insignia(c.estado), { id: "d-estado-insignia" }));
      document.getElementById("d-notas").textContent =
        "notas" in c ? (c.notas || "(sin notas)") : "(no visibles para su rol)";
      const notas = document.getElementById("notas");
      if (notas && "notas" in c) notas.value = c.notas || "";
    };
    const cargar = async () => {
      const r = await api("GET", `/api/citas/${id}`);
      if (!r.ok) return mostrarError(r);
      pintar(r.datos);
    };
    const cambiar = async (cambios, texto) => {
      const r = await api("PATCH", `/api/citas/${id}`, cambios);
      if (!r.ok) return mostrarError(r);
      mostrar(texto, "exito");
      cargar();
    };
    document.getElementById("cancelar").addEventListener("click",
      () => cambiar({ estado: "cancelada" }, "Cita cancelada."));
    document.getElementById("atendida").addEventListener("click",
      () => cambiar({ estado: "atendida" }, "Cita marcada como atendida."));
    document.getElementById("form-notas").addEventListener("submit", (ev) => {
      ev.preventDefault();
      cambiar({ notas: ev.target.notas.value }, "Notas guardadas.");
    });
    cargar();
  },

  reporte() {
    if (!exigirSesion()) return;
    const cuerpo = document.getElementById("lista-reporte");
    document.getElementById("form-reporte").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const dias = encodeURIComponent(ev.target.dias.value);
      const r = await api("GET", `/api/reportes/ocupacion?dias=${dias}`);
      if (!r.ok) { filaVacia(cuerpo, 2, "Sin datos."); return mostrarError(r); }
      const filas = Object.entries(r.datos).filter(([, total]) => total > 0);
      document.getElementById("total-reporte").textContent = filas.reduce((a, [, t]) => a + t, 0);
      if (filas.length === 0) return filaVacia(cuerpo, 2, "No hay citas en ese rango.");
      const maximo = Math.max(...filas.map(([, t]) => t));
      cuerpo.replaceChildren();
      filas.forEach(([fecha, total]) => {
        const tr = document.createElement("tr");
        celda(tr, fecha).className = "whitespace-nowrap font-medium";
        const td = celda(tr, "");
        const fila = document.createElement("div");
        fila.className = "flex items-center gap-3";
        const barra = document.createElement("div");
        barra.className = "barra-dato";
        barra.style.width = Math.max(4, Math.round((total / maximo) * 85)) + "%";
        const numero = document.createElement("span");
        numero.className = "font-semibold text-uni-azul";
        numero.textContent = String(total);
        fila.append(barra, numero);
        td.appendChild(fila);
        cuerpo.appendChild(tr);
      });
    });
  },

  docs() {},
};

document.addEventListener("DOMContentLoaded", () => {
  ajustarNavegacion();
  const pagina = document.body.dataset.pagina;
  if (paginas[pagina]) paginas[pagina]();
});
