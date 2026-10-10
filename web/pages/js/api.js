// Cliente de la API del backend. Todas las páginas lo cargan desde index.html.
const API_BASE = "/api/v1";

async function apiRequest(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = res.status === 204 ? null : await res.json().catch(() => ({}));
  if (!res.ok) {
    // Errores 422 de validación traen el detalle por campo en data.errors
    const detalle = data?.errors ? ` ${JSON.stringify(data.errors)}` : "";
    throw new Error((data?.message || `Error HTTP ${res.status}`) + detalle);
  }
  return data;
}

const api = {
  get: (path) => apiRequest(path),
  post: (path, body) =>
    apiRequest(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) }),
  delete: (path) => apiRequest(path, { method: "DELETE" }),
  upload: (path, campos) => {
    const form = new FormData();
    Object.entries(campos).forEach(([k, v]) => form.append(k, v));
    return apiRequest(path, { method: "POST", body: form });
  },
};

// Indicador de estado de la API en el menú
(async () => {
  const pill = document.getElementById("api-status");
  if (!pill) return;
  try {
    const health = await api.get("/health/");
    const ok = health.status === "ok";
    pill.textContent = ok ? "API conectada" : "API sin base de datos";
    pill.className = `ml-2 status-pill ${ok ? "status-pill--ok" : "status-pill--warn"}`;
  } catch {
    pill.textContent = "API sin conexión";
    pill.className = "ml-2 status-pill status-pill--error";
  }
})();
