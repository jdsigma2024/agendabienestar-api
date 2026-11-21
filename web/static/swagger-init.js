// Inicializa Swagger UI con la especificacion OpenAPI de AgendaBienestar.
// Va en un archivo aparte (y no en un <script> dentro del HTML) para que funcione
// con una Content-Security-Policy que no permite scripts en linea.
window.addEventListener("DOMContentLoaded", () => {
  if (typeof SwaggerUIBundle === "undefined") {
    const aviso = document.getElementById("swagger-ui");
    aviso.textContent = "No se pudo cargar Swagger UI desde el CDN (¿sin conexión a Internet?). " +
      "La especificación sigue disponible en /openapi.json.";
    return;
  }
  window.ui = SwaggerUIBundle({
    url: "/openapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    persistAuthorization: true,
    tryItOutEnabled: true,
    displayRequestDuration: true,
  });
});
