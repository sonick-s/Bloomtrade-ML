// Utilidades compartidas por todas las páginas: formato, colores, mensajes, carga de archivos y gráficos.

const fmt = {
  num: (n, dec = 0) => (n ?? 0).toLocaleString("es-EC", { minimumFractionDigits: dec, maximumFractionDigits: dec }),
  t: (kg) => `${fmt.num(kg / 1000, kg < 10000 ? 1 : 0)} t`,
  kg: (kg) => `${fmt.num(kg)} kg`,
  usd: (v) => {
    if (v == null) return "–";
    if (Math.abs(v) >= 1e6) return `$${fmt.num(v / 1e6, 2)} M`;
    if (Math.abs(v) >= 1e3) return `$${fmt.num(v / 1e3, 1)} mil`;
    return `$${fmt.num(v, 2)}`;
  },
  precio: (v) => (v == null ? "–" : `$${fmt.num(v, 2)}`),
  pct: (v, dec = 1) => (v == null ? "–" : `${fmt.num(v * 100, dec)}%`),
  fecha: (iso) => (iso ? new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("es-EC", { day: "2-digit", month: "short", year: "numeric" }) : "–"),
  mes: (iso) => new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("es-EC", { month: "short", year: "2-digit" }),
};

function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// Color fijo por mercado y flor: el mismo en todas las páginas y gráficos
const COLORES_FIJOS = {
  "Estados Unidos": "#e11d48", "Kazajistán": "#2563eb", "Países Bajos": "#059669", "Rusia": "#d97706",
  "Canadá": "#7c3aed", "Italia": "#0891b2", "España": "#d97706", "Alemania": "#7c3aed",
  "Rosas": "#e11d48", "Flores de verano": "#65a30d", "Gypsophila": "#0891b2", "Claveles": "#db2777",
  "Otros": "#94a3b8", "Otras flores": "#94a3b8",
};
const PALETA = ["#e11d48", "#2563eb", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d"];
function colorDe(nombre) {
  if (COLORES_FIJOS[nombre]) return COLORES_FIJOS[nombre];
  // Nombres nuevos: color estable calculado a partir del texto
  const hash = [...nombre].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
  return PALETA[hash % PALETA.length];
}

function confiabilidad(error) {
  if (error == null) return { clase: "badge-neutral", texto: "Sin datos" };
  if (error < 0.35) return { clase: "badge-ok", texto: "Alta" };
  if (error < 0.6) return { clase: "badge-warn", texto: "Media" };
  return { clase: "badge-error", texto: "Baja" };
}

function mostrarAlerta(contenedor, tipo, html) {
  contenedor.innerHTML = html ? `<div class="alert alert-${tipo}">${html}</div>` : "";
}

// Deshabilita el botón y muestra un texto mientras corre la acción
async function conCarga(boton, texto, accion) {
  const original = boton.innerHTML;
  boton.disabled = true;
  boton.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-current border-r-transparent rounded-full animate-spin"></span> ${texto}`;
  try {
    return await accion();
  } finally {
    boton.disabled = false;
    boton.innerHTML = original;
  }
}

// Zona para arrastrar o elegir un archivo. Llama a alElegir(file).
function prepararDropzone(zona, input, alElegir) {
  input.addEventListener("change", () => input.files[0] && alElegir(input.files[0]));
  ["dragenter", "dragover"].forEach((e) =>
    zona.addEventListener(e, (ev) => { ev.preventDefault(); zona.classList.add("dropzone--over"); }));
  ["dragleave", "drop"].forEach((e) =>
    zona.addEventListener(e, (ev) => { ev.preventDefault(); zona.classList.remove("dropzone--over"); }));
  zona.addEventListener("drop", (ev) => ev.dataTransfer.files[0] && alElegir(ev.dataTransfer.files[0]));
}

// Explica los errores de validación de un dataset (campo `errores` de la API)
function describirErrores(errores) {
  if (!errores) return "";
  if (errores.columnas_faltantes) {
    return `Faltan columnas: <strong>${errores.columnas_faltantes.map(esc).join(", ")}</strong>.
      Columnas recibidas: ${errores.columnas_recibidas.map(esc).join(", ")}`;
  }
  if (errores.filas_con_errores) {
    return "<ul class='list-disc pl-5 mt-1'>" + Object.entries(errores.filas_con_errores)
      .map(([problema, d]) => `<li>${esc(problema)}: ${d.cantidad} filas (ej. fila ${d.filas.join(", ")})</li>`)
      .join("") + "</ul>";
  }
  return esc(errores.mensaje || JSON.stringify(errores));
}

// Configuración común de Plotly
const PLOT_CONFIG = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] };
function layoutBase(extra = {}) {
  return {
    margin: { t: 10, r: 10, b: 40, l: 60 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#334155", size: 12 },
    hoverlabel: { font: { family: "Inter, sans-serif" } },
    xaxis: { gridcolor: "#f1f5f9" },
    yaxis: { gridcolor: "#e2e8f0", zeroline: false },
    legend: { orientation: "h", y: -0.18 },
    ...extra,
  };
}
