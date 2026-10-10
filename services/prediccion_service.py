"""
Recomendación de mercados para el inventario de la finca (matchmaking prescriptivo).

Para cada lote se usan los pronósticos del modelo activo en su ventana de salida y se:
  1. Descartan mercados: tránsito que no deja suficiente vida útil, precio menor al mínimo
     del lote o sin demanda esperada.
  2. Puntúan los que quedan: 60% precio esperado + 40% demanda esperada (ambos normalizados).
  3. Reparte el stock entre los 3 mejores en proporción a su puntaje.
"Otros" no se recomienda porque agrupa muchos países.
"""
from collections import defaultdict
from datetime import timedelta

from config import db
from config.global_exceptions import NotFoundException
from ml.series import OTRAS_FLORES, OTROS_MERCADOS
from models import InventarioFinca, Modelo, Pronostico
from services.dataset_service import dataset_service

PESO_PRECIO = 0.6
PESO_DEMANDA = 0.4
MAX_MERCADOS = 3
DIAS_MINIMOS_EN_DESTINO = 7  # vida útil que debe quedar al llegar para que la flor se venda
ESTADOS_EXCLUIDOS = ("despachado", "descartado")


def recomendar(dataset_id):
    dataset = dataset_service.get_of_type(dataset_id, "interno")
    modelo = db.session.scalar(db.select(Modelo).where(Modelo.activo.is_(True)))
    if modelo is None:
        raise NotFoundException("No hay un modelo activo. Entrena y activa uno en la pantalla de Modelos.")

    pronostico = _pronostico_por_serie(modelo.id)
    lotes = db.session.scalars(
        db.select(InventarioFinca)
        .where(InventarioFinca.dataset_id == dataset.id, InventarioFinca.estado.not_in(ESTADOS_EXCLUIDOS))
        .order_by(InventarioFinca.fecha_salida_desde)
    ).all()

    contexto = {
        "flores": modelo.parametros.get("flores", []),
        "transito": modelo.parametros.get("transito_dias", {}),
        "errores": (modelo.metricas or {}).get("por_serie", {}),
    }
    resultados = [_recomendar_lote(lote, pronostico, contexto) for lote in lotes]
    return {
        "dataset": {"id": dataset.id, "nombre": dataset.nombre},
        "modelo": {"id": modelo.id, "version": modelo.version, "horizonte": _horizonte(pronostico)},
        "resumen": _resumen(resultados),
        "lotes": resultados,
    }


# --------------------------------------------------------------------------- por lote

def _recomendar_lote(lote, pronostico, contexto):
    grupo = lote.tipo_flor if lote.tipo_flor in contexto["flores"] else OTRAS_FLORES
    stock = float(lote.stock_kg)
    base = {
        "id": lote.id,
        "codigo_lote": lote.codigo_lote,
        "tipo_flor": lote.tipo_flor,
        "variedad": lote.variedad,
        "grupo_modelo": grupo,
        "stock_kg": stock,
        "fecha_salida_desde": lote.fecha_salida_desde.isoformat(),
        "fecha_salida_hasta": lote.fecha_salida_hasta.isoformat(),
        "asignaciones": [],
        "descartados": [],
        "ingreso_esperado": 0.0,
        "margen_esperado": None,
    }

    mercados = _mercados_en_ventana(pronostico, grupo, lote.fecha_salida_desde, lote.fecha_salida_hasta)
    if not mercados:
        return {**base, "estado": "fuera_de_horizonte",
                "mensaje": "La ventana de salida está fuera del periodo pronosticado"}

    candidatos = []
    for mercado, datos in mercados.items():
        datos["transito"] = contexto["transito"].get(mercado)
        motivo = _motivo_descarte(lote, mercado, datos)
        if motivo:
            base["descartados"].append({"mercado": mercado, "motivo": motivo})
        else:
            candidatos.append({"mercado": mercado, **datos})

    if not candidatos:
        return {**base, "estado": "sin_mercado", "mensaje": "Ningún mercado cumple las condiciones del lote"}

    max_precio = max(c["precio"] for c in candidatos)
    max_demanda = max(c["demanda_kg"] for c in candidatos)
    for c in candidatos:
        c["puntaje"] = PESO_PRECIO * c["precio"] / max_precio + PESO_DEMANDA * c["demanda_kg"] / max_demanda
    elegidos = sorted(candidatos, key=lambda c: c["puntaje"], reverse=True)[:MAX_MERCADOS]
    total_puntaje = sum(c["puntaje"] for c in elegidos)

    costo = float(lote.costo_produccion_usd_kg) if lote.costo_produccion_usd_kg is not None else None
    asignaciones = []
    for c in elegidos:
        proporcion = c["puntaje"] / total_puntaje
        kg = stock * proporcion
        error = contexto["errores"].get(f"{grupo}|{c['mercado']}")
        asignaciones.append({
            "mercado": c["mercado"],
            "porcentaje": round(proporcion * 100, 1),
            "kg": round(kg, 1),
            "precio_esperado": round(c["precio"], 2),
            "ingreso_esperado": round(kg * c["precio"], 2),
            "margen_esperado": round(kg * (c["precio"] - costo), 2) if costo is not None else None,
            "demanda_mercado_kg": round(c["demanda_kg"], 1),
            "transito_dias": c["transito"],
            "error_modelo": error,
            "puntaje": round(c["puntaje"], 3),
        })

    ingreso = sum(a["ingreso_esperado"] for a in asignaciones)
    margen = sum(a["margen_esperado"] for a in asignaciones) if costo is not None else None
    return {**base, "estado": "ok", "asignaciones": asignaciones,
            "ingreso_esperado": round(ingreso, 2), "margen_esperado": round(margen, 2) if margen is not None else None}


def _motivo_descarte(lote, mercado, datos):
    if mercado == OTROS_MERCADOS:
        return "Agrupa varios países (no es un destino concreto)"
    if datos["demanda_kg"] <= 0:
        return "Sin demanda esperada en la ventana de salida"
    dias = datos["transito"]
    if lote.vida_util_dias is not None and dias is not None and lote.vida_util_dias - dias < DIAS_MINIMOS_EN_DESTINO:
        return (f"Tránsito de {dias:g} días deja menos de {DIAS_MINIMOS_EN_DESTINO} días de vida útil "
                f"(vida útil del lote: {lote.vida_util_dias} días)")
    minimo = lote.precio_minimo_usd_kg
    if minimo is not None and datos["precio"] < float(minimo):
        return f"Precio esperado ${datos['precio']:.2f}/kg menor al mínimo del lote (${float(minimo):.2f}/kg)"
    return None


def _mercados_en_ventana(pronostico, grupo, desde, hasta):
    """Demanda (suma) y precio (ponderado por volumen) de cada mercado en los meses de la ventana."""
    acumulado = defaultdict(lambda: {"kg": 0.0, "valor": 0.0, "precios": []})
    for (flor, mercado), meses in pronostico.items():
        if flor != grupo:
            continue
        for periodo, volumen, precio in meses:
            fin_mes = _fin_de_mes(periodo)
            if periodo <= hasta and fin_mes >= desde:
                datos = acumulado[mercado]
                datos["kg"] += volumen
                datos["valor"] += volumen * precio
                datos["precios"].append(precio)
    return {
        mercado: {
            "demanda_kg": d["kg"],
            "precio": d["valor"] / d["kg"] if d["kg"] > 0 else sum(d["precios"]) / len(d["precios"]),
        }
        for mercado, d in acumulado.items()
    }


# --------------------------------------------------------------------------- auxiliares

def _pronostico_por_serie(modelo_id):
    filas = db.session.execute(
        db.select(Pronostico.tipo_flor, Pronostico.pais_destino, Pronostico.periodo,
                  Pronostico.volumen_kg_pred, Pronostico.precio_usd_kg_pred)
        .where(Pronostico.modelo_id == modelo_id)
    ).all()
    series = defaultdict(list)
    for flor, mercado, periodo, volumen, precio in filas:
        series[(flor, mercado)].append((periodo, float(volumen), float(precio or 0)))
    return series


def _fin_de_mes(periodo):
    siguiente = periodo.replace(year=periodo.year + 1, month=1) if periodo.month == 12 else periodo.replace(month=periodo.month + 1)
    return siguiente - timedelta(days=1)


def _horizonte(pronostico):
    periodos = [p for meses in pronostico.values() for p, _, _ in meses]
    return {"desde": min(periodos).isoformat(), "hasta": max(periodos).isoformat()} if periodos else None


def _resumen(resultados):
    por_mercado = defaultdict(lambda: {"kg": 0.0, "ingreso": 0.0, "lotes": 0})
    for lote in resultados:
        for a in lote["asignaciones"]:
            datos = por_mercado[a["mercado"]]
            datos["kg"] += a["kg"]
            datos["ingreso"] += a["ingreso_esperado"]
            datos["lotes"] += 1
    margenes = [lote["margen_esperado"] for lote in resultados if lote["margen_esperado"] is not None]
    return {
        "lotes": len(resultados),
        "lotes_con_recomendacion": sum(1 for lote in resultados if lote["estado"] == "ok"),
        "lotes_sin_mercado": sum(1 for lote in resultados if lote["estado"] == "sin_mercado"),
        "lotes_fuera_de_horizonte": sum(1 for lote in resultados if lote["estado"] == "fuera_de_horizonte"),
        "stock_kg": round(sum(lote["stock_kg"] for lote in resultados), 1),
        "kg_asignados": round(sum(a["kg"] for lote in resultados for a in lote["asignaciones"]), 1),
        "ingreso_esperado": round(sum(lote["ingreso_esperado"] for lote in resultados), 2),
        "margen_esperado": round(sum(margenes), 2) if margenes else None,
        "por_mercado": [
            {"mercado": m, "kg": round(d["kg"], 1), "ingreso": round(d["ingreso"], 2), "lotes": d["lotes"]}
            for m, d in sorted(por_mercado.items(), key=lambda x: -x[1]["ingreso"])
        ],
    }
