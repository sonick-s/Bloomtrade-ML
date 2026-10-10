// Planificador de ventas: carga del inventario y recomendación de mercados por lote.
const $ = (id) => document.getElementById(id);
const estado = { resultado: null, mercado: "", flor: "", estadoLote: "", texto: "", clicConectado: false };
let archivoElegido = null;

const ETIQUETA_ESTADO = {
  ok: ["badge-ok", "Con recomendación"],
  sin_mercado: ["badge-error", "Sin mercado viable"],
  fuera_de_horizonte: ["badge-neutral", "Fuera del pronóstico"],
};

// --------------------------------------------------------------------------- carga

prepararDropzone($("dropzone"), $("archivo"), (archivo) => {
  archivoElegido = archivo;
  $("archivo-texto").textContent = archivo.name;
  if (!$("nombre").value) $("nombre").value = archivo.name.replace(/\.csv$/i, "");
  $("subir").disabled = false;
});

$("subir").addEventListener("click", () => conCarga($("subir"), "Cargando…", async () => {
  try {
    const d = await api.upload("/datasets/upload", {
      archivo: archivoElegido, nombre: $("nombre").value.trim() || archivoElegido.name, tipo: "interno",
    });
    if (d.estado === "con_errores") {
      mostrarAlerta($("carga-msg"), "error", `<strong>No se cargó.</strong> ${describirErrores(d.errores)}`);
      return;
    }
    mostrarAlerta($("carga-msg"), "ok", `${fmt.num(d.filas)} lotes cargados.`);
    $("nombre").value = "";
    $("archivo").value = "";
    $("archivo-texto").textContent = "Arrastra el CSV aquí o haz clic";
    await cargarInventarios(d.id);
    await analizar();
  } catch (err) {
    mostrarAlerta($("carga-msg"), "error", esc(err.message));
  }
}));

async function cargarInventarios(elegir = null) {
  const { items } = await api.get("/datasets/?tipo=interno&estado=validado&per_page=100");
  $("dataset").innerHTML = items.length
    ? items.map((d) => `<option value="${d.id}">${esc(d.nombre)} · ${d.filas} lotes · ${fmt.fecha(d.created_at)}</option>`).join("")
    : `<option value="">No hay inventarios cargados</option>`;
  if (elegir) $("dataset").value = elegir;
  $("analizar").disabled = !items.length;
}

// --------------------------------------------------------------------------- análisis

async function analizar() {
  const id = $("dataset").value;
  if (!id) return;
  await conCarga($("analizar"), "Calculando…", async () => {
    try {
      estado.resultado = await api.get(`/predicciones/inventario?dataset_id=${id}`);
      const r = estado.resultado;
      mostrarAlerta($("analisis-msg"), "info",
        `Pronóstico del modelo v${r.modelo.version}, de ${fmt.mes(r.modelo.horizonte.desde)} a ${fmt.mes(r.modelo.horizonte.hasta)}.`);
      Object.assign(estado, { mercado: "", flor: "", estadoLote: "", texto: "" });
      $("buscar").value = "";
      $("f-estado").value = "";
      const flores = [...new Set(r.lotes.map((l) => l.tipo_flor))].sort();
      $("f-flor").innerHTML = `<option value="">Todas las flores</option>` + flores.map((f) => `<option>${esc(f)}</option>`).join("");
      $("resultados").classList.remove("hidden");
      renderResumen();
      renderLotes();
    } catch (err) {
      $("resultados").classList.add("hidden");
      mostrarAlerta($("analisis-msg"), "error", esc(err.message));
    }
  });
}

function renderResumen() {
  const { resumen, lotes } = estado.resultado;
  $("k-lotes").textContent = resumen.lotes;
  $("k-lotes-hint").textContent = `${resumen.lotes_con_recomendacion} con recomendación · ${resumen.lotes_sin_mercado + resumen.lotes_fuera_de_horizonte} sin plan`;
  $("k-kg").textContent = fmt.t(resumen.kg_asignados);
  $("k-kg-hint").textContent = `de ${fmt.t(resumen.stock_kg)} en stock (${fmt.pct(resumen.kg_asignados / resumen.stock_kg)})`;
  $("k-ingreso").textContent = fmt.usd(resumen.ingreso_esperado);
  $("k-margen").textContent = fmt.usd(resumen.margen_esperado);
  $("k-precio").textContent = resumen.kg_asignados ? `${fmt.precio(resumen.ingreso_esperado / resumen.kg_asignados)}` : "–";

  const mercados = [...resumen.por_mercado].reverse();
  Plotly.react("g-mercados", [
    { type: "bar", orientation: "h", name: "Kilos", y: mercados.map((m) => m.mercado), x: mercados.map((m) => m.kg),
      marker: { color: mercados.map((m) => (estado.mercado && m.mercado !== estado.mercado ? "#e2e8f0" : colorDe(m.mercado))) },
      text: mercados.map((m) => `${fmt.t(m.kg)} · ${fmt.usd(m.ingreso)}`), textposition: "outside", cliponaxis: false,
      customdata: mercados.map((m) => m.lotes),
      hovertemplate: "%{y}<br>%{x:,.0f} kg en %{customdata} lotes<extra></extra>" },
  ], layoutBase({ margin: { t: 10, r: 130, b: 20, l: 110 }, xaxis: { visible: false }, showlegend: false }), PLOT_CONFIG);
  conectarClicMercados();

  // Calendario: kilos por mes de salida y mercado
  const porMes = new Map();
  lotes.forEach((l) => l.asignaciones.forEach((a) => {
    const mes = l.fecha_salida_desde.slice(0, 7) + "-01";
    const clave = `${a.mercado}|${mes}`;
    porMes.set(clave, (porMes.get(clave) || 0) + a.kg);
  }));
  const meses = [...new Set([...porMes.keys()].map((k) => k.split("|")[1]))].sort();
  Plotly.react("g-calendario", resumen.por_mercado.map((m) => ({
    type: "bar", name: m.mercado, x: meses.map(fmt.mes), y: meses.map((mes) => porMes.get(`${m.mercado}|${mes}`) || 0),
    marker: { color: colorDe(m.mercado) }, hovertemplate: `${esc(m.mercado)} · %{x}<br>%{y:,.0f} kg<extra></extra>`,
  })), layoutBase({ barmode: "stack" }), PLOT_CONFIG);
}

// Plotly agrega .on() al div después del primer gráfico: se conecta una sola vez
function conectarClicMercados() {
  if (estado.clicConectado) return;
  estado.clicConectado = true;
  $("g-mercados").on("plotly_click", (e) => {
    const mercado = e.points[0].y;
    estado.mercado = estado.mercado === mercado ? "" : mercado;
    renderResumen();
    renderLotes();
  });
}

function lotesFiltrados() {
  const texto = estado.texto.toLowerCase();
  return estado.resultado.lotes.filter((l) =>
    (!estado.flor || l.tipo_flor === estado.flor) &&
    (!estado.estadoLote || l.estado === estado.estadoLote) &&
    (!estado.mercado || l.asignaciones.some((a) => a.mercado === estado.mercado)) &&
    (!texto || `${l.codigo_lote} ${l.variedad} ${l.tipo_flor}`.toLowerCase().includes(texto)));
}

function renderLotes() {
  const lotes = lotesFiltrados();
  const filtro = estado.mercado ? ` · que se venden en ${estado.mercado} (clic de nuevo en la barra para quitar)` : "";
  $("plan-sub").textContent = `${lotes.length} de ${estado.resultado.lotes.length} lotes${filtro}`;
  $("lotes").innerHTML = lotes.length ? lotes.map(tarjetaLote).join("") : `<p class="text-slate-500 text-sm">Ningún lote coincide con los filtros.</p>`;
}

function tarjetaLote(l) {
  const [clase, texto] = ETIQUETA_ESTADO[l.estado];
  const barra = l.asignaciones.map((a) =>
    `<div class="h-full flex items-center justify-center text-[11px] font-medium text-white overflow-hidden"
          style="width:${a.porcentaje}%;background:${colorDe(a.mercado)}" title="${esc(a.mercado)}: ${a.porcentaje}%">${a.porcentaje >= 15 ? `${Math.round(a.porcentaje)}%` : ""}</div>`).join("");
  const detalle = l.asignaciones.map((a) => {
    const c = confiabilidad(a.error_modelo);
    return `<tr>
      <td><span class="inline-block w-2.5 h-2.5 rounded-full mr-2" style="background:${colorDe(a.mercado)}"></span>${esc(a.mercado)}</td>
      <td class="num">${a.porcentaje}%</td><td class="num">${fmt.kg(a.kg)}</td><td class="num">${fmt.precio(a.precio_esperado)}</td>
      <td class="num">${fmt.usd(a.ingreso_esperado)}</td><td class="num">${fmt.usd(a.margen_esperado)}</td>
      <td class="num">${a.transito_dias ?? "–"} días</td><td class="num">${fmt.t(a.demanda_mercado_kg)}</td>
      <td><span class="badge ${c.clase}">${c.texto}</span></td></tr>`;
  }).join("");
  const descartados = l.descartados.filter((d) => d.mercado !== "Otros")
    .map((d) => `<li><strong>${esc(d.mercado)}:</strong> ${esc(d.motivo)}</li>`).join("");

  return `<details class="border border-slate-200 rounded-xl group">
    <summary class="list-none cursor-pointer p-4 grid md:grid-cols-12 gap-3 items-center hover:bg-slate-50 rounded-xl">
      <div class="md:col-span-3">
        <div class="font-semibold">${esc(l.codigo_lote || `Lote ${l.id}`)}</div>
        <div class="text-xs text-slate-500">${esc(l.tipo_flor)}${l.variedad ? ` · ${esc(l.variedad)}` : ""} · ${fmt.kg(l.stock_kg)}</div>
      </div>
      <div class="md:col-span-2 text-xs text-slate-500">Salida<br><span class="text-slate-700">${fmt.fecha(l.fecha_salida_desde)} – ${fmt.fecha(l.fecha_salida_hasta)}</span></div>
      <div class="md:col-span-4">
        ${l.estado === "ok"
          ? `<div class="h-6 rounded-md overflow-hidden flex bg-slate-100">${barra}</div>
             <div class="text-xs text-slate-500 mt-1">${l.asignaciones.map((a) => `${Math.round(a.porcentaje)}% ${esc(a.mercado)}`).join(" · ")}</div>`
          : `<span class="badge ${clase}">${texto}</span> <span class="text-xs text-slate-500">${esc(l.mensaje || "")}</span>`}
      </div>
      <div class="md:col-span-3 text-right">
        <div class="font-semibold tabular-nums">${l.estado === "ok" ? fmt.usd(l.ingreso_esperado) : "–"}</div>
        <div class="text-xs text-slate-500">${l.margen_esperado != null ? `margen ${fmt.usd(l.margen_esperado)}` : ""}
          <span class="ml-1 inline-block transition-transform group-open:rotate-180">▾</span></div>
      </div>
    </summary>
    <div class="px-4 pb-4 border-t border-slate-100">
      ${l.asignaciones.length ? `<div class="overflow-x-auto mt-3"><table class="tabla">
        <thead><tr><th>Mercado</th><th class="num">%</th><th class="num">Kilos</th><th class="num">Precio/kg</th><th class="num">Ingreso</th>
          <th class="num">Margen</th><th class="num">Tránsito</th><th class="num">Demanda del mercado</th><th>Confiabilidad</th></tr></thead>
        <tbody>${detalle}</tbody></table></div>` : ""}
      ${descartados ? `<p class="text-xs font-semibold text-slate-600 mt-3">Mercados descartados</p><ul class="text-xs text-slate-500 list-disc pl-5 mt-1 space-y-0.5">${descartados}</ul>` : ""}
    </div>
  </details>`;
}

// --------------------------------------------------------------------------- eventos

$("analizar").addEventListener("click", analizar);
$("dataset").addEventListener("change", analizar);
$("buscar").addEventListener("input", (e) => { estado.texto = e.target.value; renderLotes(); });
$("f-flor").addEventListener("change", (e) => { estado.flor = e.target.value; renderLotes(); });
$("f-estado").addEventListener("change", (e) => { estado.estadoLote = e.target.value; renderLotes(); });
(async () => {
  await cargarInventarios();
  if ($("dataset").value) await analizar();
})();
