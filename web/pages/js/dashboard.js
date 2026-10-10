// Dashboard global: carga todo con una llamada y filtra/agrega en el navegador.
const estado = { datos: null, flor: "", mercado: "", metrica: "volumen_kg" };
const $ = (id) => document.getElementById(id);

const NOMBRE_METRICA = { volumen_kg: "Volumen (kg)", valor_usd: "Valor FOB (USD)" };
const formatoMetrica = (v) => (estado.metrica === "valor_usd" ? fmt.usd(v) : fmt.t(v));

// --------------------------------------------------------------------------- datos

function filtrar(filas, { ignorarFlor = false, ignorarMercado = false } = {}) {
  return filas.filter((f) =>
    (ignorarFlor || !estado.flor || f.flor === estado.flor) &&
    (ignorarMercado || !estado.mercado || f.mercado === estado.mercado));
}

function sumarPor(filas, clave, campo = estado.metrica) {
  const totales = new Map();
  filas.forEach((f) => totales.set(f[clave], (totales.get(f[clave]) || 0) + (f[campo] || 0)));
  return totales;
}

const suma = (filas, campo) => filas.reduce((s, f) => s + (f[campo] || 0), 0);

function ultimos12(filas) {
  const periodos = [...new Set(estado.datos.historico.map((h) => h.periodo))].sort().slice(-12);
  return filas.filter((f) => periodos.includes(f.periodo));
}

// Error del modelo al nivel de detalle que se está viendo
function errorDelNivel() {
  const m = estado.datos.modelo_activo;
  if (estado.flor && estado.mercado) {
    return { error: m.error_por_serie[`${estado.flor}|${estado.mercado}`], nivel: "esta flor en este mercado, por mes" };
  }
  if (estado.mercado) return { error: m.wape_mercado_mes, nivel: "por mercado y mes" };
  return { error: m.wape_total_mes, nivel: estado.flor ? "total mensual (referencia)" : "total mensual" };
}

function errorDeMercado(mercado) {
  if (estado.flor) return estado.datos.modelo_activo.error_por_serie[`${estado.flor}|${mercado}`];
  // Sin flor elegida: promedio de las flores del mercado ponderado por su volumen
  const porFlor = sumarPor(estado.datos.pronostico.filter((f) => f.mercado === mercado), "flor", "volumen_kg");
  let total = 0;
  let acumulado = 0;
  porFlor.forEach((vol, flor) => {
    const e = estado.datos.modelo_activo.error_por_serie[`${flor}|${mercado}`];
    if (e != null) {
      acumulado += e * vol;
      total += vol;
    }
  });
  return total ? acumulado / total : null;
}

function variacion(actual, previo) {
  if (!previo) return "–";
  const sube = actual >= previo;
  return `<span class="${sube ? "text-emerald-600" : "text-rose-600"}">${sube ? "+" : ""}${fmt.pct(actual / previo - 1)}</span>`;
}

// --------------------------------------------------------------------------- render

function render() {
  const pron = filtrar(estado.datos.pronostico);
  const hist = filtrar(estado.datos.historico);
  renderKpis(pron, hist);
  renderSerie(pron, hist);
  renderMercados();
  renderFlores();
  renderCalor();
  renderTabla();
  $("f-flor").value = estado.flor;
  $("f-mercado").value = estado.mercado;
}

function renderKpis(pron, hist) {
  const vol = suma(pron, "volumen_kg");
  const valor = suma(pron, "valor_usd");
  const previo = suma(ultimos12(hist), "volumen_kg");
  $("k-vol").textContent = fmt.t(vol);
  $("k-vol-var").innerHTML = previo ? `${variacion(vol, previo)} vs últimos 12 meses` : "sin historia para comparar";
  $("k-valor").textContent = fmt.usd(valor);
  $("k-precio").textContent = vol ? `${fmt.precio(valor / vol)}/kg` : "–";

  const [mesPico, valorPico] = [...sumarPor(pron, "periodo")].sort((a, b) => b[1] - a[1])[0] || [];
  $("k-pico").textContent = mesPico ? fmt.mes(mesPico) : "–";
  $("k-pico-hint").textContent = mesPico ? formatoMetrica(valorPico) : "";

  const { error, nivel } = errorDelNivel();
  const c = confiabilidad(error);
  $("k-conf").innerHTML = `<span class="badge ${c.clase} text-base">${c.texto}</span>`;
  $("k-conf-hint").textContent = error != null ? `error ${fmt.pct(error)} · ${nivel}` : nivel;
}

function renderSerie(pron, hist) {
  const h = sumarPor(hist, "periodo");
  const p = sumarPor(pron, "periodo");
  const xh = [...h.keys()].sort();
  const xp = [...p.keys()].sort();
  const banda = Math.min(errorDelNivel().error ?? 1, 1);
  // El pronóstico arranca en el último mes real para que la línea sea continua
  const xpUnida = [xh.at(-1), ...xp];
  const ypUnida = [h.get(xh.at(-1)), ...xp.map((x) => p.get(x))];

  const etiqueta = `Ecuador → ${estado.mercado || "todos los destinos"} · ${estado.flor || "todas las flores"}`;
  $("t-serie").textContent = `${etiqueta} · ${NOMBRE_METRICA[estado.metrica]}`;
  const unidad = estado.metrica === "valor_usd" ? "$%{y:,.0f}" : "%{y:,.0f} kg";
  const hover = `%{x|%b %Y}<br>${unidad}<extra>%{fullData.name}</extra>`;

  Plotly.react("g-serie", [
    { x: xp, y: xp.map((x) => p.get(x) * (1 + banda)), mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x: xp, y: xp.map((x) => p.get(x) * (1 - banda)), mode: "lines", line: { width: 0 }, fill: "tonexty",
      fillcolor: "rgba(225,29,72,0.10)", name: "Rango de error", hoverinfo: "skip" },
    { x: xh, y: xh.map((x) => h.get(x)), mode: "lines+markers", name: "Histórico real",
      line: { color: "#334155", width: 2 }, marker: { size: 4 }, hovertemplate: hover },
    { x: xpUnida, y: ypUnida, mode: "lines+markers", name: "Pronóstico",
      line: { color: "#e11d48", width: 2.5, dash: "dot" }, marker: { size: 5 }, hovertemplate: hover },
  ], layoutBase({
    hovermode: "x unified",
    shapes: [{ type: "line", x0: xh.at(-1), x1: xh.at(-1), yref: "paper", y0: 0, y1: 1, line: { color: "#cbd5e1", dash: "dash" } }],
    annotations: [{ x: xh.at(-1), yref: "paper", y: 1, text: "último dato real", showarrow: false, xanchor: "left", font: { color: "#94a3b8", size: 11 } }],
  }), PLOT_CONFIG);
}

function renderMercados() {
  const totales = [...sumarPor(filtrar(estado.datos.pronostico, { ignorarMercado: true }), "mercado")]
    .sort((a, b) => a[1] - b[1]);
  Plotly.react("g-mercados", [{
    type: "bar",
    orientation: "h",
    y: totales.map((t) => t[0]),
    x: totales.map((t) => t[1]),
    marker: { color: totales.map((t) => (estado.mercado && t[0] !== estado.mercado ? "#e2e8f0" : colorDe(t[0]))) },
    text: totales.map((t) => formatoMetrica(t[1])),
    textposition: "outside",
    cliponaxis: false,
    hovertemplate: "%{y}<br>%{text}<extra></extra>",
  }], layoutBase({ margin: { t: 10, r: 80, b: 20, l: 120 }, xaxis: { visible: false } }), PLOT_CONFIG);
}

function renderFlores() {
  const totales = [...sumarPor(filtrar(estado.datos.pronostico, { ignorarFlor: true }), "flor")];
  Plotly.react("g-flores", [{
    type: "pie",
    hole: 0.55,
    sort: false,
    labels: totales.map((t) => t[0]),
    values: totales.map((t) => t[1]),
    marker: { colors: totales.map((t) => colorDe(t[0])), line: { color: "#fff", width: 2 } },
    pull: totales.map((t) => (t[0] === estado.flor ? 0.08 : 0)),
    textinfo: "percent",
    hovertemplate: "%{label}<br>%{percent}<extra></extra>",
  }], layoutBase({ margin: { t: 10, r: 10, b: 10, l: 10 }, legend: { orientation: "h", y: -0.05 } }), PLOT_CONFIG);
}

function renderCalor() {
  const filas = filtrar(estado.datos.pronostico, { ignorarMercado: true });
  const periodos = [...new Set(filas.map((f) => f.periodo))].sort();
  const mercados = [...sumarPor(filas, "mercado")].sort((a, b) => a[1] - b[1]).map((t) => t[0]);
  const celdas = new Map();
  filas.forEach((f) => {
    const clave = `${f.mercado}|${f.periodo}`;
    celdas.set(clave, (celdas.get(clave) || 0) + f[estado.metrica]);
  });
  const unidad = estado.metrica === "valor_usd" ? "$%{z:,.0f}" : "%{z:,.0f} kg";
  Plotly.react("g-calor", [{
    type: "heatmap",
    x: periodos.map(fmt.mes),
    y: mercados,
    z: mercados.map((m) => periodos.map((p) => celdas.get(`${m}|${p}`) || 0)),
    colorscale: [[0, "#fff1f3"], [0.5, "#fb7185"], [1, "#9f1239"]],
    showscale: false,
    xgap: 2,
    ygap: 2,
    hovertemplate: `%{y} · %{x}<br>${unidad}<extra></extra>`,
  }], layoutBase({ margin: { t: 10, r: 10, b: 40, l: 120 } }), PLOT_CONFIG);
}

function renderTabla() {
  const pron = filtrar(estado.datos.pronostico, { ignorarMercado: true });
  const hist = ultimos12(filtrar(estado.datos.historico, { ignorarMercado: true }));
  const volumen = sumarPor(pron, "mercado", "volumen_kg");
  const previo = sumarPor(hist, "mercado", "volumen_kg");
  const filas = [...sumarPor(pron, "mercado", "valor_usd")].sort((a, b) => b[1] - a[1]).map(([mercado, valor]) => {
    const vol = volumen.get(mercado);
    const pico = [...sumarPor(pron.filter((f) => f.mercado === mercado), "periodo", "volumen_kg")]
      .sort((a, b) => b[1] - a[1])[0]?.[0];
    const c = confiabilidad(errorDeMercado(mercado));
    return `<tr class="cursor-pointer ${mercado === estado.mercado ? "bg-brand-50" : ""}" data-mercado="${esc(mercado)}">
      <td><span class="inline-block w-2.5 h-2.5 rounded-full mr-2" style="background:${colorDe(mercado)}"></span>${esc(mercado)}</td>
      <td class="num">${fmt.t(vol)}</td><td class="num">${variacion(vol, previo.get(mercado))}</td>
      <td class="num">${fmt.precio(vol ? valor / vol : null)}</td><td class="num">${fmt.usd(valor)}</td>
      <td>${pico ? fmt.mes(pico) : "–"}</td><td><span class="badge ${c.clase}">${c.texto}</span></td></tr>`;
  });
  $("t-mercados").innerHTML = filas.join("");
}

function renderModelo() {
  const m = estado.datos.modelo_activo;
  $("m-info").textContent = `Versión ${m.version} · entrenado ${fmt.fecha(m.entrenado)} · ${fmt.num(m.registros)} registros · datos hasta ${fmt.mes(m.ultimo_mes)}`;
  const niveles = [
    ["Flor × mercado × mes", m.wape, m.wape_base],
    ["Mercado × mes", m.wape_mercado_mes, m.wape_base_mercado_mes],
    ["Total × mes", m.wape_total_mes, m.wape_base_total_mes],
    ["Total del año", m.error_total_anio, null],
    ["Precio por kg", m.wape_precio, null],
  ];
  $("t-modelo").innerHTML = niveles.map(([nombre, error, base]) => {
    let comparacion = "";
    if (base != null) {
      comparacion = error <= base
        ? "<span class='badge badge-ok'>mejor que la base</span>"
        : "<span class='badge badge-warn'>peor que la base</span>";
    }
    return `<tr><td>${nombre}</td><td class="num font-medium">${fmt.pct(error)}</td><td class="num">${fmt.pct(base)}</td><td>${comparacion}</td></tr>`;
  }).join("");
}

// --------------------------------------------------------------------------- inicio

function llenarSelect(select, opciones, todos) {
  select.innerHTML = `<option value="">${todos}</option>` + opciones.map((o) => `<option>${esc(o)}</option>`).join("");
}

function mostrarVacio(datos) {
  $("subtitulo").textContent = "Todavía no hay un modelo activo";
  $("vacio").classList.remove("hidden");
  $("vacio").innerHTML = `<div class="card text-center py-12">
    <p class="text-lg font-semibold">Aún no hay pronósticos para mostrar</p>
    <p class="text-slate-500 mt-1">Hay ${fmt.num(datos.registros_mercado)} registros de mercado en ${datos.datasets_mercado} dataset(s).
      Carga un CSV de exportaciones y entrena un modelo para ver el dashboard.</p>
    <a href="/modelos" class="btn btn-primary mt-4">Ir a Modelos</a></div>`;
}

function conectarEventos() {
  $("f-flor").addEventListener("change", (e) => { estado.flor = e.target.value; render(); });
  $("f-mercado").addEventListener("change", (e) => { estado.mercado = e.target.value; render(); });
  $("limpiar").addEventListener("click", () => { estado.flor = ""; estado.mercado = ""; render(); });
  document.querySelectorAll("[data-metrica]").forEach((boton) => boton.addEventListener("click", () => {
    estado.metrica = boton.dataset.metrica;
    document.querySelectorAll("[data-metrica]").forEach((b) => b.classList.toggle("chip--active", b === boton));
    render();
  }));
  // Clic en una barra o porción: filtra por ese mercado o flor (otro clic lo quita)
  $("g-mercados").on("plotly_click", (e) => {
    const mercado = e.points[0].y;
    estado.mercado = estado.mercado === mercado ? "" : mercado;
    render();
  });
  $("g-flores").on("plotly_click", (e) => {
    const flor = e.points[0].label;
    estado.flor = estado.flor === flor ? "" : flor;
    render();
  });
  $("t-mercados").addEventListener("click", (e) => {
    const fila = e.target.closest("tr[data-mercado]");
    if (!fila) return;
    estado.mercado = estado.mercado === fila.dataset.mercado ? "" : fila.dataset.mercado;
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

async function iniciar() {
  try {
    estado.datos = await api.get("/dashboard/resumen");
  } catch (err) {
    $("subtitulo").textContent = "";
    $("vacio").classList.remove("hidden");
    mostrarAlerta($("vacio"), "error", `No se pudo cargar el dashboard: ${esc(err.message)}`);
    return;
  }
  const m = estado.datos.modelo_activo;
  if (!m || !estado.datos.pronostico.length) {
    mostrarVacio(estado.datos.datos);
    return;
  }

  const d = estado.datos.datos;
  $("subtitulo").textContent = `Modelo v${m.version} · ${fmt.num(d.registros_mercado)} registros de mercado · `
    + `${d.lotes_inventario} lotes en inventario (${fmt.t(d.stock_kg)})`;
  llenarSelect($("f-flor"), m.flores, "Todas las flores");
  llenarSelect($("f-mercado"), m.mercados, "Ecuador → todos los destinos");
  $("filtros").classList.remove("hidden");
  $("contenido").classList.remove("hidden");
  renderModelo();
  render();
  conectarEventos();
}

iniciar();
