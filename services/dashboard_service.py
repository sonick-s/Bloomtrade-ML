"""
Resumen global para el dashboard. Devuelve los datos por serie (flor × mercado) para que la
página pueda filtrar y agregar en el navegador sin volver a llamar a la API.
"""
from config import db
from ml.series import OTRAS_FLORES, OTROS_MERCADOS
from models import Dataset, Exportacion, InventarioFinca, Modelo, Pronostico

MESES_HISTORICO = 36


def resumen():
    modelo = db.session.scalar(db.select(Modelo).where(Modelo.activo.is_(True)))
    return {
        "datos": _estado_datos(),
        "modelo_activo": _modelo(modelo),
        "historico": _historico(modelo),
        "pronostico": _pronostico(modelo) if modelo else [],
    }


def _estado_datos():
    por_tipo = dict(db.session.execute(
        db.select(Dataset.tipo, db.func.count()).where(Dataset.estado == "validado").group_by(Dataset.tipo)
    ).all())
    lotes, stock = db.session.execute(
        db.select(db.func.count(), db.func.coalesce(db.func.sum(InventarioFinca.stock_kg), 0))
        .where(InventarioFinca.estado.not_in(("despachado", "descartado")))
    ).one()
    return {
        "datasets_mercado": por_tipo.get("mercado", 0),
        "datasets_internos": por_tipo.get("interno", 0),
        "registros_mercado": db.session.scalar(db.select(db.func.count(Exportacion.id))),
        "lotes_inventario": lotes,
        "stock_kg": float(stock),
    }


def _modelo(modelo):
    if modelo is None:
        return None
    metricas, parametros = modelo.metricas or {}, modelo.parametros or {}
    return {
        "id": modelo.id,
        "version": modelo.version,
        "entrenado": modelo.created_at.isoformat(),
        "registros": parametros.get("registros"),
        "mercados": parametros.get("mercados", []),
        "flores": parametros.get("flores", []),
        "ultimo_mes": parametros.get("ultimo_mes"),
        "wape": metricas.get("wape"),
        "wape_base": metricas.get("wape_base_serie_mes"),
        "wape_mercado_mes": metricas.get("wape_mercado_mes"),
        "wape_base_mercado_mes": metricas.get("wape_base_mercado_mes"),
        "wape_total_mes": metricas.get("wape_total_mes"),
        "wape_base_total_mes": metricas.get("wape_base_total_mes"),
        "error_total_anio": metricas.get("error_total_anio"),
        "wape_precio": metricas.get("wape_precio"),
        "error_por_serie": metricas.get("por_serie", {}),
    }


def _historico(modelo):
    """
    Volumen y valor mensual real de los últimos meses, agrupado igual que el modelo activo
    (mercados principales + "Otros"). Sin modelo, se devuelve solo el total.
    """
    ultimo = db.session.execute(
        db.select(Exportacion.anio, Exportacion.mes).order_by(Exportacion.anio.desc(), Exportacion.mes.desc()).limit(1)
    ).first()
    if ultimo is None:
        return []
    anio, mes = ultimo
    indice_desde = anio * 12 + mes - MESES_HISTORICO

    consulta = (
        db.select(Exportacion.anio, Exportacion.mes, Exportacion.tipo_flor, Exportacion.pais_destino,
                  db.func.sum(Exportacion.volumen_kg), db.func.sum(Exportacion.valor_fob_usd))
        .where(Exportacion.anio * 12 + Exportacion.mes > indice_desde)
        .group_by(Exportacion.anio, Exportacion.mes, Exportacion.tipo_flor, Exportacion.pais_destino)
    )
    if modelo is not None:
        consulta = consulta.where(Exportacion.dataset_id.in_(modelo.dataset_ids))

    mercados = set((modelo.parametros or {}).get("mercados", [])) if modelo else set()
    flores = set((modelo.parametros or {}).get("flores", [])) if modelo else set()
    agrupado = {}
    for anio, mes, flor, pais, volumen, valor in db.session.execute(consulta):
        clave = (
            f"{anio:04d}-{mes:02d}-01",
            (flor if flor in flores else OTRAS_FLORES) if modelo else "Todas",
            (pais if pais in mercados else OTROS_MERCADOS) if modelo else "Todos",
        )
        fila = agrupado.setdefault(clave, [0.0, 0.0])
        fila[0] += float(volumen)
        fila[1] += float(valor)
    return [
        {"periodo": p, "flor": f, "mercado": m, "volumen_kg": round(v, 2), "valor_usd": round(val, 2)}
        for (p, f, m), (v, val) in sorted(agrupado.items())
    ]


def _pronostico(modelo):
    filas = db.session.execute(
        db.select(Pronostico.periodo, Pronostico.tipo_flor, Pronostico.pais_destino, Pronostico.volumen_kg_pred,
                  Pronostico.precio_usd_kg_pred, Pronostico.limite_inf, Pronostico.limite_sup)
        .where(Pronostico.modelo_id == modelo.id)
        .order_by(Pronostico.periodo)
    ).all()
    return [
        {
            "periodo": periodo.isoformat(),
            "flor": flor,
            "mercado": mercado,
            "volumen_kg": float(volumen),
            "precio_kg": float(precio) if precio is not None else None,
            "valor_usd": round(float(volumen) * float(precio or 0), 2),
            "limite_inf": float(inf or 0),
            "limite_sup": float(sup or 0),
        }
        for periodo, flor, mercado, volumen, precio, inf, sup in filas
    ]
