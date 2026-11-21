// Prueba de ESTRES del reporte de ocupacion (hallazgo H8).
// Uso:  k6 run -e TOKEN="<token de admin>" -e DIAS=50000 k6/estres.js
// Compare los resultados contra la version vulnerable y la corregida.
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE || 'http://127.0.0.1:5000';
const DIAS = __ENV.DIAS || '50000';

export const options = {
  stages: [
    { duration: '30s', target: 5 },   // carga normal
    { duration: '30s', target: 20 },  // estres
    { duration: '30s', target: 40 },  // por encima del limite
    { duration: '20s', target: 0 },   // recuperacion
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // Una peticion normal (30 dias) y una abusiva (DIAS) en cada iteracion.
  const h = { headers: { Authorization: `Bearer ${__ENV.TOKEN}` } };
  const normal = http.get(`${BASE}/api/reportes/ocupacion?dias=30`, h);
  check(normal, { 'reporte normal responde 200': (r) => r.status === 200 });
  const abuso = http.get(`${BASE}/api/reportes/ocupacion?dias=${DIAS}`, h,
    { responseCallback: http.expectedStatuses(200, 400) });
  check(abuso, { 'abuso rechazado (400)': (r) => r.status === 400 });
  sleep(1);
}
