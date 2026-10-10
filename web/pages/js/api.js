// Cliente mínimo para la API del backend. Todas las páginas lo cargan desde base.html.
const API_BASE = "/api/v1";

async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiPostFile(path, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
  return data;
}

// Indicador de estado de la API en el menú
(async () => {
  const pill = document.getElementById("api-status");
  if (!pill) return;
  try {
    const health = await apiGet("/health/");
    const ok = health.status === "ok";
    pill.textContent = ok ? "API conectada" : "API sin base de datos";
    pill.className = `ml-3 status-pill ${ok ? "status-pill--ok" : "status-pill--warn"}`;
  } catch {
    pill.textContent = "API sin conexión";
    pill.className = "ml-3 status-pill status-pill--error";
  }
})();
