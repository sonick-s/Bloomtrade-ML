// Vista previa del CSV en el navegador. Cuando exista el endpoint de predicción,
// se reemplaza la lectura local por: apiPostFile("/model/predict", file)
const REQUIRED = ["Fecha_Despacho", "Tipo_Flor", "Pais_Destino", "Volumen_Kg", "Valor_FOB_USD"];
const COLORS = ["#e11d48", "#059669", "#2563eb", "#d97706", "#7c3aed", "#0891b2"];
const PLOT_CONFIG = { responsive: true, displayModeBar: false };
const BASE_LAYOUT = {
  margin: { t: 10, r: 10, b: 40, l: 60 },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, sans-serif", color: "#334155" },
};

const input = document.getElementById("csv-input");
const dropzone = document.getElementById("dropzone");
const fileInfo = document.getElementById("file-info");
const fileError = document.getElementById("file-error");

input.addEventListener("change", () => input.files[0] && handleFile(input.files[0]));

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("dropzone--over"); })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("dropzone--over"); })
);
dropzone.addEventListener("drop", (e) => e.dataTransfer.files[0] && handleFile(e.dataTransfer.files[0]));

async function handleFile(file) {
  fileError.classList.add("hidden");
  try {
    const rows = parseCsv(await file.text());
    const missing = REQUIRED.filter((c) => !(c in rows[0]));
    if (missing.length) throw new Error(`Faltan columnas: ${missing.join(", ")}`);

    fileInfo.textContent = `${file.name} · ${rows.length.toLocaleString("es-EC")} registros`;
    fileInfo.classList.remove("hidden");
    render(rows);
  } catch (err) {
    fileError.textContent = err.message;
    fileError.classList.remove("hidden");
    document.getElementById("results").classList.add("hidden");
  }
}

// Parser simple: sirve para CSV sin comas dentro de los valores
function parseCsv(text) {
  const lines = text.replace(/^﻿/, "").trim().split(/\r?\n/);
  if (lines.length < 2) throw new Error("El archivo está vacío");
  const headers = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    return Object.fromEntries(headers.map((h, i) => [h, values[i]]));
  });
}

function sumBy(rows, key, value) {
  const totals = {};
  for (const r of rows) totals[r[key]] = (totals[r[key]] || 0) + Number(r[value] || 0);
  return totals;
}

const fmt = (n, opts = {}) => n.toLocaleString("es-EC", { maximumFractionDigits: 0, ...opts });

function render(rows) {
  document.getElementById("results").classList.remove("hidden");

  const kg = rows.reduce((s, r) => s + Number(r.Volumen_Kg || 0), 0);
  const fob = rows.reduce((s, r) => s + Number(r.Valor_FOB_USD || 0), 0);
  document.getElementById("kpi-rows").textContent = fmt(rows.length);
  document.getElementById("kpi-kg").textContent = `${fmt(kg / 1000)} t`;
  document.getElementById("kpi-fob").textContent = `$${fmt(fob / 1e6, { maximumFractionDigits: 1 })} M`;
  document.getElementById("kpi-price").textContent = `$${(fob / kg).toFixed(2)}`;

  // Volumen por mes
  const monthly = sumBy(rows.map((r) => ({ ...r, mes: r.Fecha_Despacho.slice(0, 7) })), "mes", "Volumen_Kg");
  const months = Object.keys(monthly).sort();
  Plotly.newPlot("chart-monthly", [{
    x: months, y: months.map((m) => monthly[m]), type: "scatter", mode: "lines",
    line: { color: COLORS[0], width: 2 }, fill: "tozeroy", fillcolor: "rgba(225,29,72,0.08)",
    hovertemplate: "%{x}<br>%{y:,.0f} kg<extra></extra>",
  }], { ...BASE_LAYOUT, xaxis: { showgrid: false }, yaxis: { gridcolor: "#e2e8f0" } }, PLOT_CONFIG);

  // Participación por flor
  const flowers = Object.entries(sumBy(rows, "Tipo_Flor", "Volumen_Kg")).sort((a, b) => b[1] - a[1]);
  Plotly.newPlot("chart-flowers", [{
    labels: flowers.map((f) => f[0]), values: flowers.map((f) => f[1]), type: "pie", hole: 0.55,
    marker: { colors: COLORS }, textinfo: "percent", sort: false,
  }], { ...BASE_LAYOUT, margin: { t: 10, r: 10, b: 10, l: 10 }, legend: { orientation: "h" } }, PLOT_CONFIG);

  // Top 10 destinos
  const countries = Object.entries(sumBy(rows, "Pais_Destino", "Valor_FOB_USD"))
    .sort((a, b) => b[1] - a[1]).slice(0, 10).reverse();
  Plotly.newPlot("chart-countries", [{
    y: countries.map((c) => c[0]), x: countries.map((c) => c[1]), type: "bar", orientation: "h",
    marker: { color: COLORS[1] }, hovertemplate: "%{y}<br>$%{x:,.0f}<extra></extra>",
  }], { ...BASE_LAYOUT, margin: { t: 10, r: 10, b: 40, l: 160 }, xaxis: { gridcolor: "#e2e8f0" } }, PLOT_CONFIG);
}
