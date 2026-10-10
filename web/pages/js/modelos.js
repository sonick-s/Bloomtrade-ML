// Pantalla de Modelos: carga de CSV de mercado, selección de datasets, entrenamiento y versiones.
const $ = (id) => document.getElementById(id);
let archivoElegido = null;

// --------------------------------------------------------------------------- 1. carga

prepararDropzone($("dropzone"), $("archivo"), (archivo) => {
  archivoElegido = archivo;
  $("archivo-texto").textContent = `${archivo.name} · ${fmt.num(archivo.size / 1024)} KB`;
  if (!$("nombre").value) $("nombre").value = archivo.name.replace(/\.csv$/i, "");
  $("subir").disabled = false;
  mostrarAlerta($("carga-msg"), "", "");
});

$("subir").addEventListener("click", () => conCarga($("subir"), "Validando e insertando…", async () => {
  try {
    const dataset = await api.upload("/datasets/upload", {
      archivo: archivoElegido,
      nombre: $("nombre").value.trim() || archivoElegido.name,
      tipo: "mercado",
    });
    if (dataset.estado === "con_errores") {
      mostrarAlerta($("carga-msg"), "error", `<strong>El archivo tiene errores y no se cargó.</strong> ${describirErrores(dataset.errores)}`);
    } else {
      mostrarAlerta($("carga-msg"), "ok",
        `Cargado: <strong>${fmt.num(dataset.filas)}</strong> registros del ${fmt.fecha(dataset.fecha_min)} al ${fmt.fecha(dataset.fecha_max)}.
         Ya puedes entrenar con él.`);
      archivoElegido = null;
      $("archivo").value = "";
      $("archivo-texto").textContent = "Arrastra el CSV aquí o haz clic para elegirlo";
      $("nombre").value = "";
    }
    await cargarDatasets(dataset.estado === "validado" ? dataset.id : null);
  } catch (err) {
    mostrarAlerta($("carga-msg"), "error", esc(err.message));
  }
}));

// --------------------------------------------------------------------------- 2. datasets

async function cargarDatasets(marcarId = null) {
  const marcados = new Set(seleccionados());
  if (marcarId) marcados.add(marcarId);
  const { items } = await api.get("/datasets/?tipo=mercado&per_page=100");
  if (!items.length) {
    $("t-datasets").innerHTML = `<tr><td colspan="7" class="text-slate-500">Todavía no hay datasets. Carga un CSV para empezar.</td></tr>`;
    return;
  }
  // Por defecto se marcan todos los validados
  const marcarTodos = marcados.size === 0;
  $("t-datasets").innerHTML = items.map((d) => {
    const valido = d.estado === "validado";
    const marcado = valido && (marcarTodos || marcados.has(d.id));
    const estado = valido ? "badge-ok" : d.estado === "con_errores" ? "badge-error" : "badge-neutral";
    return `<tr>
      <td><input type="checkbox" class="sel-dataset accent-brand-500 w-4 h-4" value="${d.id}" ${marcado ? "checked" : ""} ${valido ? "" : "disabled"}></td>
      <td><div class="font-medium">${esc(d.nombre)}</div><div class="text-xs text-slate-400">${esc(d.archivo_original)} · id ${d.id}</div></td>
      <td class="num">${fmt.num(d.filas)}</td>
      <td>${d.fecha_min ? `${fmt.mes(d.fecha_min)} – ${fmt.mes(d.fecha_max)}` : "–"}</td>
      <td><span class="badge ${estado}">${d.estado.replace("_", " ")}</span></td>
      <td class="text-slate-500">${fmt.fecha(d.created_at)}</td>
      <td><button class="btn btn-secondary btn-sm" data-eliminar="${d.id}" data-nombre="${esc(d.nombre)}">Eliminar</button></td>
    </tr>`;
  }).join("");
}

function seleccionados() {
  return [...document.querySelectorAll(".sel-dataset:checked")].map((c) => Number(c.value));
}

$("t-datasets").addEventListener("click", async (e) => {
  const boton = e.target.closest("[data-eliminar]");
  if (!boton) return;
  if (!confirm(`¿Eliminar el dataset "${boton.dataset.nombre}" y todos sus registros?`)) return;
  try {
    await api.delete(`/datasets/${boton.dataset.eliminar}`);
    await cargarDatasets();
  } catch (err) {
    // 409: el dataset se usó para entrenar un modelo (se protege la trazabilidad)
    mostrarAlerta($("carga-msg"), "error", `No se pudo eliminar: ${esc(err.message)}. Elimina primero los modelos entrenados con él.`);
  }
});

$("recargar").addEventListener("click", () => cargarDatasets());

// --------------------------------------------------------------------------- 3. entrenar

$("entrenar").addEventListener("click", () => {
  const ids = seleccionados();
  if (!ids.length) {
    mostrarAlerta($("entreno-msg"), "error", "Marca al menos un dataset de mercado validado.");
    return;
  }
  return conCarga($("entrenar"), "Entrenando…", async () => {
    mostrarAlerta($("entreno-msg"), "info", "Entrenando y validando el modelo…");
    $("entreno-detalle").innerHTML = "";
    try {
      const r = await api.post("/modelos/entrenar", { dataset_ids: ids, activar_si_mejora: $("activar").checked });
      mostrarAlerta($("entreno-msg"), r.activado ? "ok" : "info", esc(r.mensaje));
      $("entreno-detalle").innerHTML = detalleMetricas(r.modelo);
      await cargarModelos();
    } catch (err) {
      mostrarAlerta($("entreno-msg"), "error", esc(err.message));
    }
  });
});

function detalleMetricas(modelo) {
  const m = modelo.metricas;
  const p = modelo.parametros;
  const filas = [
    ["Flor × mercado × mes", m.wape_serie_mes, m.wape_base_serie_mes],
    ["Mercado × mes", m.wape_mercado_mes, m.wape_base_mercado_mes],
    ["Total × mes", m.wape_total_mes, m.wape_base_total_mes],
    ["Total del año", m.error_total_anio, null],
    ["Precio por kg", m.wape_precio, null],
  ].map(([nivel, e, base]) => `<tr><td>${nivel}</td><td class="num font-medium">${fmt.pct(e)}</td><td class="num">${fmt.pct(base)}</td></tr>`);
  return `<div class="grid md:grid-cols-2 gap-4 mt-4">
    <table class="tabla"><thead><tr><th>Nivel</th><th class="num">Error modelo</th><th class="num">Línea base</th></tr></thead>
      <tbody>${filas.join("")}</tbody></table>
    <div class="text-sm text-slate-600 space-y-1">
      <p><strong>Datos:</strong> ${fmt.num(p.registros)} registros, ${fmt.mes(p.inicio)} a ${fmt.mes(p.ultimo_mes)}</p>
      <p><strong>Mercados modelados:</strong> ${p.mercados.map(esc).join(", ")}</p>
      <p><strong>Flores modeladas:</strong> ${p.flores.map(esc).join(", ")}</p>
      <p><strong>Hiperparámetros elegidos:</strong> alpha ${m.alpha}, corrección de sesgo ${m.corregir_sesgo ? "sí" : "no"}, lags ${p.lags.join("/")}</p>
      <p><strong>Pronóstico:</strong> ${p.horizonte} meses a partir de ${fmt.mes(p.ultimo_mes)}</p>
    </div></div>`;
}

// --------------------------------------------------------------------------- 4. versiones

async function cargarModelos() {
  const { items } = await api.get("/modelos/?per_page=100");
  if (!items.length) {
    $("t-modelos").innerHTML = `<tr><td colspan="9" class="text-slate-500">Aún no hay modelos entrenados.</td></tr>`;
    return;
  }
  $("t-modelos").innerHTML = items.map((m) => {
    const met = m.metricas || {};
    const par = m.parametros || {};
    const accion = m.activo
      ? `<span class="text-xs text-slate-400">en uso</span>`
      : `<button class="btn btn-secondary btn-sm" data-activar="${m.id}">Activar</button>`;
    return `<tr class="${m.activo ? "bg-emerald-50/50" : ""}">
      <td class="font-semibold">v${m.version}</td>
      <td class="text-slate-500">${fmt.fecha(m.created_at)}</td>
      <td class="num">${fmt.num(par.registros)}</td>
      <td class="text-xs text-slate-500 max-w-64 truncate" title="${esc((par.mercados || []).join(", "))}">${esc((par.mercados || []).join(", "))}</td>
      <td class="num">${fmt.pct(met.wape)}</td>
      <td class="num">${fmt.pct(met.wape_total_mes)}</td>
      <td class="num">${fmt.pct(met.wape_precio)}</td>
      <td>${m.activo ? "<span class='badge badge-ok'>Activo</span>" : "<span class='badge badge-neutral'>Inactivo</span>"}</td>
      <td>${accion}</td></tr>`;
  }).join("");
}

$("t-modelos").addEventListener("click", async (e) => {
  const boton = e.target.closest("[data-activar]");
  if (!boton) return;
  await conCarga(boton, "Activando…", async () => {
    try {
      const m = await api.post(`/modelos/${boton.dataset.activar}/activar`);
      mostrarAlerta($("modelos-msg"), "ok", `Modelo v${m.version} activado. El dashboard y las predicciones ya lo usan.`);
    } catch (err) {
      mostrarAlerta($("modelos-msg"), "error", esc(err.message));
    }
  });
  await cargarModelos();
});

cargarDatasets();
cargarModelos();
