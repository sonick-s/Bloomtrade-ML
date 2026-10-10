"""
Paso 3 - Dashboard en HTML y CSS puros (sin JavaScript).

Los gráficos son SVG generados aquí mismo. Las pestañas por flor y el selector de país
usan solo CSS (radio buttons + selector :checked) y los tooltips son <title> de SVG.
El resultado es un único archivo que se abre con doble clic.
"""
import math
from html import escape

import pandas as pd

from datos import FLORES, MERCADOS
from modelo import wape

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                "septiembre", "octubre", "noviembre", "diciembre"]
MESES_HISTORIA = 36


# --------------------------------------------------------------------------- formato

def _num(valor, decimales=0):
    """Formato español: 12.345,6"""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def _toneladas(kg):
    # Un decimal en volúmenes chicos para que no aparezcan como "0 t"
    return f"{_num(kg / 1000, 1 if kg < 10_000 else 0)} t"


def _usd(valor):
    if valor >= 1e6:
        return f"${_num(valor / 1e6, 1)} M"
    if valor >= 1e3:
        return f"${_num(valor / 1e3)} mil"
    return f"${_num(valor)}"


def _pct(valor):
    return f"{_num(valor * 100, 1)}%"


def _mes(fecha, largo=False):
    """'feb 27' o 'febrero 2027'"""
    if largo:
        return f"{MESES_LARGOS[fecha.month - 1]} {fecha.year}"
    return f"{MESES[fecha.month - 1]} {fecha:%y}"


# --------------------------------------------------------------------------- gráfico SVG

def _tope(maximo):
    """Redondea el máximo del eje Y a un valor 'bonito' (1, 2, 2.5, 5 × 10^n)."""
    if maximo <= 0:
        return 1
    base = 10 ** math.floor(math.log10(maximo))
    return next(f * base for f in (1, 2, 2.5, 5, 10) if maximo <= f * base)


def _divisiones(tope):
    """Cantidad de líneas guía para que cada paso sea redondo (250 -> 5 pasos de 50)."""
    mantisa = round(tope / 10 ** math.floor(math.log10(tope)), 1)
    return 5 if mantisa in (2.5, 5) else 4


NOMBRES_LINEA = {"s-real": "Real", "s-modelo": "Modelo", "s-base": "Línea base", "s-pron": "Pronóstico"}


def grafico(fechas, lineas, *, zonas=()):
    """
    fechas: meses del eje X. lineas: lista de (clase_css, valores) alineados con fechas; None = sin dato.
    zonas: lista de (índice_inicio, clase_css); cada zona se sombrea hasta la siguiente o hasta el final.
    Cada punto lleva un <title>: el navegador lo muestra como tooltip al pasar el mouse (sin JavaScript).
    """
    ancho, alto = 760, 280
    izq, der, arr, aba = 52, 14, 14, 30
    w, h, n = ancho - izq - der, alto - arr - aba, len(fechas)
    paso_x = w / (n - 1)
    valores = [v for _, serie in lineas for v in serie if v is not None]
    tope = _tope(max(valores, default=1))

    def x(i):
        return izq + paso_x * i

    def y(v):
        return arr + h * (1 - v / tope)

    partes = [f'<svg viewBox="0 0 {ancho} {alto}" class="chart" role="img">']
    finales = [inicio for inicio, _ in zonas[1:]] + [n]
    for (inicio, clase), fin in zip(zonas, finales):
        x0 = x(inicio) - paso_x / 2
        x1 = izq + w if fin >= n else x(fin) - paso_x / 2
        partes.append(f'<rect class="{clase}" x="{x0:.1f}" y="{arr}" width="{x1 - x0:.1f}" height="{h}"/>')

    divisiones = _divisiones(tope)
    for k in range(divisiones + 1):
        valor = tope * k / divisiones
        yy = y(valor)
        partes.append(f'<line class="grid" x1="{izq}" x2="{izq + w}" y1="{yy:.1f}" y2="{yy:.1f}"/>')
        partes.append(f'<text class="eje" x="{izq - 6}" y="{yy + 3:.1f}" text-anchor="end">'
                      f'{_num(valor, 1 if tope < 10 else 0)}</text>')

    for i in range(0, n, max(1, round(n / 9))):
        partes.append(f'<text class="eje" x="{x(i):.1f}" y="{alto - 6}" text-anchor="middle">{_mes(fechas[i])}</text>')

    for clase, serie in lineas:
        trazo, abierto = [], False
        for i, v in enumerate(serie):
            if v is None:
                abierto = False
                continue
            trazo.append(f"{'L' if abierto else 'M'}{x(i):.1f},{y(v):.1f}")
            abierto = True
        partes.append(f'<path class="{clase}" d="{" ".join(trazo)}"/>')

    for clase, serie in lineas:
        for i, v in enumerate(serie):
            if v is not None:
                partes.append(
                    f'<circle class="pt {clase}" cx="{x(i):.1f}" cy="{y(v):.1f}" r="6">'
                    f'<title>{_mes(fechas[i], largo=True)} · {NOMBRES_LINEA[clase]}: {_num(v, 1)} t</title></circle>'
                )

    partes.append("</svg>")
    return "".join(partes)


def _leyenda(*items):
    return '<div class="leyenda">' + "".join(
        f'<span><i class="sw {clase}"></i>{escape(texto)}</span>' for clase, texto in items
    ) + "</div>"


# --------------------------------------------------------------------------- secciones

def _seccion_validacion(panel, test, resumen):
    """Gráfico del total mensual: lo real vs lo que el modelo y la línea base predijeron."""
    total = panel.groupby("periodo")["volumen_kg"].sum()
    fechas = list(total.index[-MESES_HISTORIA:])
    pred = test.groupby("periodo")[["volumen_pred", "base_pred"]].sum()
    inicio_test = fechas.index(pred.index.min())

    def alinear(serie):
        return [serie.get(f) / 1000 if f in serie.index else None for f in fechas]

    svg = grafico(fechas, [
        ("s-base", alinear(pred["base_pred"])),
        ("s-modelo", alinear(pred["volumen_pred"])),
        ("s-real", alinear(total)),
    ], zonas=[(inicio_test, "zona-val")])

    filas = []
    for mercado in MERCADOS:
        g = test[test["mercado"] == mercado]
        e_mod, e_base = wape(g["volumen_kg"], g["volumen_pred"]), wape(g["volumen_kg"], g["base_pred"].fillna(0))
        gana = "gana" if e_mod < e_base else "pierde"
        filas.append(
            f"<tr><td>{escape(mercado)}</td><td class='num'>{_toneladas(g['volumen_kg'].sum())}</td>"
            f"<td class='num'>{_pct(e_mod)}</td><td class='num'>{_pct(e_base)}</td>"
            f"<td><span class='tag tag-{gana}'>{'mejor' if gana == 'gana' else 'peor'}</span></td></tr>"
        )

    return f"""
    <section class="card">
      <h2>1 · ¿El modelo aprende? Validación con el último año</h2>
      <p class="nota">El modelo se entrenó solo con datos hasta {_mes(resumen['corte_test'], largo=True)}
      y predijo los 12 meses siguientes (zona sombreada), que ya conocemos. Así se mide su error real.
      Pasa el mouse sobre la línea para ver cada valor.</p>
      {_leyenda(("s-real", "Real"), ("s-modelo", "Modelo (Ridge)"), ("s-base", "Línea base: igual que hace un año"))}
      {svg}
      <p class="eje-titulo">Volumen total mensual, toneladas</p>
      <h3>Error por mercado en el periodo de validación</h3>
      <div class="tabla-scroll"><table>
        <thead><tr><th>Mercado</th><th class='num'>Volumen real</th><th class='num'>Error modelo</th>
        <th class='num'>Error línea base</th><th>Modelo vs base</th></tr></thead>
        <tbody>{''.join(filas)}</tbody>
      </table></div>
    </section>"""


def _nombre_mercado(mercado):
    return "Otros (resto de países)" if mercado == "Otros" else mercado


def _confiabilidad(error):
    if math.isnan(error):
        return "baja", "Sin ventas recientes"
    if error < 0.35:
        return "alta", "Alta"
    if error < 0.60:
        return "media", "Media"
    return "baja", "Baja"


def _precio(valor):
    return "–" if valor is None or math.isnan(valor) else f"${_num(valor, 2)}"


def _variacion(nuevo, anterior):
    if not anterior:
        return "<span class='muted'>–</span>"
    cambio = nuevo / anterior - 1
    clase = "sube" if cambio >= 0 else "baja-txt"
    return f"<span class='{clase}'>{'+' if cambio >= 0 else ''}{_num(cambio * 100)}%</span>"


def _datos_vista(flor, panel, test, pronostico):
    """Filtra una flor (o suma todas si flor es None) y agrupa por mercado y mes."""
    if flor is not None:
        panel, test, pronostico = (d[d["flor"] == flor] for d in (panel, test, pronostico))
    claves = ["mercado", "periodo"]
    historia = panel.groupby(claves, as_index=False)["volumen_kg"].sum()
    validacion = test.groupby(claves, as_index=False)[["volumen_kg", "volumen_pred", "base_pred"]].sum()
    futuro = (
        pronostico.assign(valor_pred=pronostico["volumen_pred"] * pronostico["precio_pred"])
        .groupby(claves, as_index=False)[["volumen_pred", "valor_pred"]].sum()
    )
    futuro["precio_pred"] = futuro["valor_pred"] / futuro["volumen_pred"].where(futuro["volumen_pred"] > 0)
    return historia, validacion, futuro


class _Eje:
    """Meses del gráfico de una vista: historia reciente + meses pronosticados."""

    def __init__(self, historia, validacion, futuro):
        self.hist = sorted(historia["periodo"].unique())[-MESES_HISTORIA:]
        self.fut = sorted(futuro["periodo"].unique())
        self.fechas = [*self.hist, *self.fut]
        self.inicio_val = self.hist.index(validacion["periodo"].min())

    def lineas(self, hist, fut, val=None):
        """Real en la historia, modelo en la validación y pronóstico unido al último mes real."""
        vacio_fut = [None] * len(self.fut)
        real = [hist.get(f, 0) / 1000 for f in self.hist] + vacio_fut
        pron = [None] * (len(self.hist) - 1) + [real[len(self.hist) - 1]] + [fut.get(f, 0) / 1000 for f in self.fut]
        lineas = [("s-real", real), ("s-pron", pron)]
        if val is not None:
            modelo = [val.get(f) / 1000 if f in val.index else None for f in self.hist] + vacio_fut
            lineas.insert(1, ("s-modelo", modelo))
        return lineas

    def zonas(self, con_validacion):
        zonas = [(len(self.hist), "zona")]
        return [(self.inicio_val, "zona-val"), *zonas] if con_validacion else zonas


def _vista(v, nombre, historia, validacion, futuro):
    """Contenido de una pestaña: resumen, ranking de mercados y explorador por país."""
    eje = _Eje(historia, validacion, futuro)
    total_fut = futuro.groupby("periodo")["volumen_pred"].sum()
    grafico_total = grafico(
        eje.fechas, eje.lineas(historia.groupby("periodo")["volumen_kg"].sum(), total_fut), zonas=eje.zonas(False)
    )

    ranking = futuro.groupby("mercado")[["volumen_pred", "valor_pred"]].sum()
    ranking["precio"] = ranking["valor_pred"] / ranking["volumen_pred"].where(ranking["volumen_pred"] > 0)
    ranking = ranking.sort_values("valor_pred", ascending=False)
    total_vol, total_valor = ranking["volumen_pred"].sum(), ranking["valor_pred"].sum()

    # "Otros" agrupa muchos países: se muestra, pero no se recomienda
    paises = ranking.drop(index="Otros")
    mejor_valor, mejor_precio = paises.index[0], paises["precio"].idxmax()
    pico_total = total_fut.idxmax()

    filas, barras, detalles, entradas = [], [], [], []
    for mercado, fila in ranking.iterrows():
        j = MERCADOS.index(mercado)
        id_pais = f"v{v}m{j}"
        serie_fut = futuro[futuro["mercado"] == mercado].set_index("periodo")
        serie_hist = historia[historia["mercado"] == mercado].set_index("periodo")["volumen_kg"]
        serie_val = validacion[validacion["mercado"] == mercado].set_index("periodo")
        error = wape(serie_val["volumen_kg"], serie_val["volumen_pred"])
        clase, texto = _confiabilidad(error)
        pico = serie_fut["volumen_pred"].idxmax()

        filas.append(
            f"<tr><td><label for='{id_pais}' class='link'>{escape(_nombre_mercado(mercado))}</label></td>"
            f"<td class='num'>{_toneladas(fila['volumen_pred'])}</td>"
            f"<td class='num'>{_pct(fila['volumen_pred'] / total_vol)}</td>"
            f"<td class='num'>{_precio(fila['precio'])}</td><td class='num'>{_usd(fila['valor_pred'])}</td>"
            f"<td>{_mes(pico)}</td><td><span class='tag tag-{clase}'>{texto}</span></td></tr>"
        )
        entradas.append(
            f'<input type="radio" name="pais{v}" id="{id_pais}" class="tab-input"'
            f'{" checked" if mercado == mejor_valor else ""}>'
        )
        barras.append(
            f"<label for='{id_pais}' class='barra'><span class='barra-nombre'>{escape(mercado)}</span>"
            f"<span class='barra-pista'><span class='barra-relleno' "
            f"style='width:{100 * fila['valor_pred'] / ranking['valor_pred'].max():.1f}%'></span></span>"
            f"<span class='barra-valor'>{_usd(fila['valor_pred'])}</span></label>"
        )
        detalles.append(_detalle_pais(
            id_pais, mercado, nombre, eje, fila, serie_hist, serie_fut, serie_val, error, clase, texto
        ))

    return f"""
      <div class="resumen-flor">
        <div><span class="kpi-label">Volumen esperado 12 meses</span><strong>{_toneladas(total_vol)}</strong></div>
        <div><span class="kpi-label">Valor FOB esperado</span><strong>{_usd(total_valor)}</strong></div>
        <div><span class="kpi-label">Mes de mayor demanda</span><strong>{_mes(pico_total, largo=True)}</strong></div>
      </div>
      <p class="recomendacion">Para <strong>{escape(nombre.lower())}</strong>, el mayor valor esperado está en
      <strong>{escape(mejor_valor)}</strong> y el mejor precio por kilo en <strong>{escape(mejor_precio)}</strong>
      ({_precio(paises.loc[mejor_precio, 'precio'])}/kg). La demanda total alcanza su pico en
      <strong>{_mes(pico_total, largo=True)}</strong>.</p>
      {_leyenda(("s-real", "Histórico real"), ("s-pron", "Pronóstico"))}
      {grafico_total}
      <p class="eje-titulo">Volumen mensual de {escape(nombre.lower())}, toneladas</p>

      <h3>¿A qué mercado apuntar?</h3>
      <div class="tabla-scroll"><table>
        <thead><tr><th>Mercado</th><th class='num'>Volumen 12 m</th><th class='num'>Participación</th>
        <th class='num'>Precio esperado/kg</th><th class='num'>Valor esperado</th><th>Mes pico</th>
        <th>Confiabilidad</th></tr></thead>
        <tbody>{''.join(filas)}</tbody>
      </table></div>

      <h3>Explorar por país</h3>
      <p class="nota">Elige un mercado (aquí o en la tabla) para ver su detalle. La barra es el valor FOB esperado.</p>
      <div class="explorar">
        {''.join(entradas)}
        <div class="selector">{''.join(barras)}</div>
        {''.join(detalles)}
      </div>"""


def _detalle_pais(id_pais, mercado, nombre, eje, fila, serie_hist, serie_fut, serie_val, error, clase, texto):
    ultimo_año = serie_hist[serie_hist.index > eje.hist[-1] - pd.DateOffset(months=12)].sum()
    error_base = wape(serie_val["volumen_kg"], serie_val["base_pred"])
    svg = grafico(eje.fechas, eje.lineas(serie_hist, serie_fut["volumen_pred"], serie_val["volumen_pred"]),
                  zonas=eje.zonas(True))

    picos = set(serie_fut["volumen_pred"].nlargest(3).index)
    filas = []
    for periodo, mes in serie_fut.iterrows():
        anterior = serie_hist.get(periodo - pd.DateOffset(months=12), 0)
        etiqueta = "<span class='tag tag-pico'>pico</span>" if periodo in picos else ""
        filas.append(
            f"<tr><td>{_mes(periodo, largo=True)} {etiqueta}</td><td class='num'>{_toneladas(mes['volumen_pred'])}</td>"
            f"<td class='num'>{_variacion(mes['volumen_pred'], anterior)}</td>"
            f"<td class='num'>{_precio(mes['precio_pred'])}</td><td class='num'>{_usd(mes['valor_pred'])}</td></tr>"
        )

    return f"""
        <div class="detalle det-{id_pais}">
          <h4>{escape(_nombre_mercado(mercado))} · {escape(nombre)}</h4>
          <div class="resumen-flor">
            <div><span class="kpi-label">Volumen 12 meses</span><strong>{_toneladas(fila['volumen_pred'])}</strong>
              <small>{_variacion(fila['volumen_pred'], ultimo_año)} vs últimos 12 meses</small></div>
            <div><span class="kpi-label">Precio esperado</span><strong>{_precio(fila['precio'])}/kg</strong></div>
            <div><span class="kpi-label">Valor esperado</span><strong>{_usd(fila['valor_pred'])}</strong></div>
            <div><span class="kpi-label">Confiabilidad</span><strong><span class='tag tag-{clase}'>{texto}</span></strong>
              <small>error {_pct(error) if not math.isnan(error) else '–'} · base {_pct(error_base) if not math.isnan(error_base) else '–'}</small></div>
          </div>
          {_leyenda(("s-real", "Real"), ("s-modelo", "Modelo en validación"), ("s-pron", "Pronóstico"))}
          {svg}
          <p class="eje-titulo">Toneladas por mes · zona gris: validación · zona rosa: pronóstico</p>
          <div class="tabla-scroll"><table>
            <thead><tr><th>Mes</th><th class='num'>Volumen</th><th class='num'>vs mismo mes año anterior</th>
            <th class='num'>Precio/kg</th><th class='num'>Valor</th></tr></thead>
            <tbody>{''.join(filas)}</tbody>
          </table></div>
        </div>"""


VISTAS = [("Todas las flores", None), *((flor, flor) for flor in FLORES)]


def _seccion_pronostico(panel, test, pronostico, resumen):
    entradas = "".join(
        f'<input type="radio" name="flor" id="tab{i}" class="tab-input"{" checked" if i == 0 else ""}>'
        for i in range(len(VISTAS))
    )
    etiquetas = "".join(f'<label for="tab{i}">{escape(nombre)}</label>' for i, (nombre, _) in enumerate(VISTAS))
    paneles = "".join(
        f'<div class="panel panel{i}">{_vista(i, nombre, *_datos_vista(flor, panel, test, pronostico))}</div>'
        for i, (nombre, flor) in enumerate(VISTAS)
    )
    return f"""
    <section class="card">
      <h2>2 · Pronóstico: {_mes(pronostico['periodo'].min(), largo=True)} a {_mes(pronostico['periodo'].max(), largo=True)}</h2>
      <p class="nota">El modelo se reentrenó con todos los datos hasta {_mes(resumen['ultimo_mes'], largo=True)}.
      Elige una flor:</p>
      <div class="tabs-wrap">{entradas}<nav class="tabs">{etiquetas}</nav>{paneles}</div>
    </section>"""


def _css_interactivo():
    """Reglas que muestran la pestaña y el país elegidos (selector :checked, sin JavaScript)."""
    activo = "background:var(--accent);color:#fff;border-color:var(--accent)"
    reglas = []
    for v in range(len(VISTAS)):
        reglas.append(f'#tab{v}:checked ~ .tabs label[for="tab{v}"]{{{activo}}}')
        reglas.append(f"#tab{v}:checked ~ .panel{v}{{display:block}}")
        for j in range(len(MERCADOS)):
            reglas.append(f"#v{v}m{j}:checked ~ .det-v{v}m{j}{{display:block}}")
            reglas.append(f'#v{v}m{j}:checked ~ .selector label[for="v{v}m{j}"]'
                          "{border-color:var(--accent);background:var(--zona)}")
    return "\n".join(reglas)


# --------------------------------------------------------------------------- página

def construir(panel, test, pronostico, resumen):
    valor_total = (pronostico["volumen_pred"] * pronostico["precio_pred"]).sum()
    mejora = 1 - resumen["wape_modelo"] / resumen["wape_base"]
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Experimento de pronóstico</title>
<style>
:root {{
  --bg: #f6f7f9; --card: #ffffff; --text: #1f2933; --muted: #64707d; --line: #e3e7ec;
  --accent: #c8264f; --real: #1f2933; --modelo: #c8264f; --base: #8a96a3; --pron: #c8264f;
  --zona: rgba(200, 38, 79, .07); --zona-val: rgba(100, 112, 125, .09); --ok: #0f7a55; --ok-bg: #e2f5ec; --warn: #9a6200; --warn-bg: #fdf1d8;
  --bad: #b42335; --bad-bg: #fde6e9;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #12161b; --card: #1b2128; --text: #e6e9ed; --muted: #9aa5b1; --line: #2c343d;
    --accent: #ff5c84; --real: #e6e9ed; --modelo: #ff5c84; --base: #7d8996; --pron: #ff5c84;
    --zona: rgba(255, 92, 132, .09); --zona-val: rgba(154, 165, 177, .08); --ok: #4fd1a1; --ok-bg: #173a2e; --warn: #f3c062; --warn-bg: #3d3018;
    --bad: #ff8593; --bad-bg: #44212a;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 32px 16px 64px; }}
header h1 {{ margin: 0 0 4px; font-size: 1.7rem; letter-spacing: -.01em; }}
header p {{ margin: 0; color: var(--muted); }}
h2 {{ font-size: 1.2rem; margin: 0 0 6px; }}
h3 {{ font-size: 1rem; margin: 26px 0 10px; }}
.card {{ min-width: 0; background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 22px; margin-top: 22px; }}
.nota {{ color: var(--muted); margin: 0 0 14px; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 22px; }}
.kpi {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }}
.kpi-label {{ display: block; font-size: .78rem; color: var(--muted); }}
.kpi strong {{ display: block; font-size: 1.6rem; margin-top: 2px; font-variant-numeric: tabular-nums; }}
.kpi small {{ color: var(--muted); }}
.kpi.destacado {{ border-color: var(--accent); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart .grid {{ stroke: var(--line); stroke-width: 1; }}
.chart .eje {{ fill: var(--muted); font-size: 10px; }}
.chart .zona {{ fill: var(--zona); }}
.chart .zona-val {{ fill: var(--zona-val); }}
.chart .pt {{ fill: transparent; stroke: none; cursor: crosshair; }}
.chart .pt:hover {{ fill: var(--accent); }}
.chart path {{ fill: none; stroke-linejoin: round; stroke-linecap: round; }}
.s-real {{ stroke: var(--real); stroke-width: 2; }}
.s-modelo {{ stroke: var(--modelo); stroke-width: 2.2; }}
.s-base {{ stroke: var(--base); stroke-width: 1.6; stroke-dasharray: 5 4; }}
.s-pron {{ stroke: var(--pron); stroke-width: 2.4; stroke-dasharray: 6 3; }}
.eje-titulo {{ margin: 4px 0 0; font-size: .78rem; color: var(--muted); text-align: right; }}
.leyenda {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: .85rem; color: var(--muted); margin-bottom: 6px; }}
.leyenda span {{ display: inline-flex; align-items: center; gap: 6px; }}
.sw {{ display: inline-block; width: 22px; height: 0; border-top: 2.5px solid; }}
.sw.s-real {{ border-color: var(--real); }}
.sw.s-modelo {{ border-color: var(--modelo); }}
.sw.s-base {{ border-color: var(--base); border-top-style: dashed; }}
.sw.s-pron {{ border-color: var(--pron); border-top-style: dashed; }}
table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }}
th {{ font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); font-weight: 600; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.tabla-scroll {{ overflow-x: auto; }}
.tag {{ font-size: .75rem; padding: 2px 8px; border-radius: 999px; font-weight: 600; }}
.tag-gana, .tag-alta {{ color: var(--ok); background: var(--ok-bg); }}
.tag-media {{ color: var(--warn); background: var(--warn-bg); }}
.tag-pierde, .tag-baja {{ color: var(--bad); background: var(--bad-bg); }}
.tab-input {{ position: absolute; opacity: 0; pointer-events: none; }}
.tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }}
.tabs label {{ padding: 7px 14px; border: 1px solid var(--line); border-radius: 999px; cursor: pointer; font-weight: 500; }}
.tabs label:hover {{ border-color: var(--accent); }}
.panel {{ display: none; }}
{_css_interactivo()}
.resumen-flor {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 14px; }}
.resumen-flor div {{ border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; }}
.resumen-flor strong {{ font-size: 1.25rem; }}
.recomendacion {{ background: var(--zona); border-left: 3px solid var(--accent); padding: 12px 14px; border-radius: 8px; margin: 0 0 16px; }}
.link {{ cursor: pointer; border-bottom: 1px dashed var(--muted); }}
.link:hover {{ color: var(--accent); border-color: var(--accent); }}
.muted {{ color: var(--muted); }}
.sube {{ color: var(--ok); }}
.baja-txt {{ color: var(--bad); }}
.tag-pico {{ color: var(--accent); background: var(--zona); margin-left: 4px; }}
.selector {{ display: grid; gap: 6px; margin-bottom: 18px; }}
.barra {{ display: grid; grid-template-columns: 150px 1fr 80px; align-items: center; gap: 10px;
  padding: 6px 10px; border: 1px solid var(--line); border-radius: 10px; cursor: pointer; font-size: .9rem; }}
.barra:hover {{ border-color: var(--accent); }}
.barra-pista {{ height: 10px; background: var(--bg); border-radius: 999px; overflow: hidden; }}
.barra-relleno {{ display: block; height: 100%; background: var(--accent); border-radius: 999px; }}
.barra-valor {{ text-align: right; font-variant-numeric: tabular-nums; color: var(--muted); }}
.detalle {{ display: none; border: 1px solid var(--line); border-radius: 12px; padding: 16px; }}
.detalle h4 {{ margin: 0 0 12px; font-size: 1.05rem; }}
.resumen-flor small {{ display: block; color: var(--muted); font-size: .78rem; margin-top: 2px; }}
@media (max-width: 560px) {{
  .barra {{ grid-template-columns: 1fr 70px; }}
  .barra-pista {{ grid-column: 1 / -1; grid-row: 2; }}
}}
ol {{ padding-left: 20px; margin: 0; }}
ol li {{ margin-bottom: 8px; }}
code {{ background: var(--bg); padding: 1px 5px; border-radius: 4px; font-size: .88em; }}
.aviso {{ font-size: .85rem; color: var(--muted); margin-top: 18px; }}
</style>
</head>
<body>
<main>
  <header>
    <h1>Experimento: pronóstico de demanda florícola</h1>
    <p>Exportaciones de flores de Ecuador · {_mes(panel['periodo'].min(), largo=True)} a
    {_mes(resumen['ultimo_mes'], largo=True)} · {panel.groupby(['flor', 'mercado']).ngroups} series
    ({len(FLORES)} flores × {len(MERCADOS)} mercados)</p>
  </header>

  <div class="kpis">
    <div class="kpi destacado"><span class="kpi-label">Error del modelo (validación)</span>
      <strong>{_pct(resumen['wape_modelo'])}</strong><small>WAPE del volumen</small></div>
    <div class="kpi"><span class="kpi-label">Error de la línea base</span>
      <strong>{_pct(resumen['wape_base'])}</strong><small>"igual que hace un año"</small></div>
    <div class="kpi"><span class="kpi-label">Error inevitable (piso)</span>
      <strong>{_pct(resumen['piso_error'])}</strong><small>ruido propio de los datos</small></div>
    <div class="kpi"><span class="kpi-label">Mejora sobre la base</span>
      <strong>{_pct(mejora)}</strong><small>menos error</small></div>
    <div class="kpi"><span class="kpi-label">Error del precio</span>
      <strong>{_pct(resumen['wape_precio'])}</strong><small>USD por kg</small></div>
    <div class="kpi"><span class="kpi-label">Valor FOB esperado 12 m</span>
      <strong>{_usd(valor_total)}</strong><small>todas las flores</small></div>
  </div>

  {_seccion_validacion(panel, test, resumen)}
  {_seccion_pronostico(panel, test, pronostico, resumen)}

  <section class="card">
    <h2>3 · Cómo funciona el experimento</h2>
    <ol>
      <li><strong>Datos.</strong> Los envíos del CSV se suman por mes en {panel.groupby(['flor', 'mercado']).ngroups}
      series (flor × mercado). Los países pequeños se agrupan en "Otros" y las flores menores en "Otras flores",
      porque con tan pocos envíos por mes no hay patrón que aprender.</li>
      <li><strong>Variables.</strong> Para cada mes el modelo ve: qué serie es, el mes del año por mercado y por flor
      (temporadas), la tendencia, el volumen del mismo mes hace 1, 2 y 3 años, el nivel de los 12 meses previos
      y marcas de COVID. Todo se conoce con 12 meses de anticipación, así que no hay "trampa" con datos futuros.</li>
      <li><strong>Modelo.</strong> Regresión Ridge sobre <code>log(volumen + 1)</code>, escrita con numpy.
      Es una regresión lineal con una penalización (<code>alpha = {resumen['alpha']}</code>) que evita que los
      coeficientes se disparen. Un solo modelo aprende de las {panel.groupby(['flor', 'mercado']).ngroups} series a la vez.</li>
      <li><strong>Elección de alpha.</strong> Se probaron {len(resumen['errores_validacion'])} valores entrenando hasta
      un año antes de la validación; se eligió el de menor error.</li>
      <li><strong>Validación.</strong> Se entrena hasta {_mes(resumen['corte_test'], largo=True)} y se compara contra
      los 12 meses reales siguientes. El error se mide con <strong>WAPE</strong> (suma de errores / suma real) y no con
      MAPE, porque hay meses con 0 kg donde el MAPE se vuelve infinito.</li>
      <li><strong>Pronóstico.</strong> Se reentrena con todos los datos y se predicen volumen y precio de los
      próximos 12 meses. El valor esperado es volumen × precio.</li>
    </ol>
    <p class="aviso">Los datos son sintéticos (calibrados con la ficha sectorial CFN/BCE), así que el pronóstico
    sirve para aprender y validar el método, no para decisiones comerciales reales. El piso de error se calculó
    generando 15 datasets con otras semillas: el {_pct(resumen['piso_error'])} es el error que tendría incluso un
    modelo perfecto, por el azar de los envíos individuales.</p>
  </section>
</main>
</body>
</html>
"""
