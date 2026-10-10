"""Convierte registros de exportación en series mensuales por (flor, mercado)."""
import numpy as np
import pandas as pd

OTROS_MERCADOS = "Otros"
OTRAS_FLORES = "Otras flores"
COLUMNAS_REQUERIDAS = ["fecha_despacho", "tipo_flor", "pais_destino", "volumen_kg", "valor_fob_usd"]


def elegir_grupos(registros, n_mercados=6, participacion_min_flor=0.10, meses_recientes=24):
    """
    Decide qué se modela por separado. Con pocos envíos por mes, los países y flores pequeños
    no tienen patrón que aprender, así que se agrupan:
      - mercados: los n con más valor FOB en los últimos meses; el resto va a "Otros"
      - flores: las que tienen al menos 10% del volumen; el resto va a "Otras flores"
    Valores elegidos comparando el error de validación de varias combinaciones.
    """
    fechas = registros["fecha_despacho"]
    recientes = registros[fechas > fechas.max() - pd.DateOffset(months=meses_recientes)]
    mercados = recientes.groupby("pais_destino")["valor_fob_usd"].sum().nlargest(n_mercados).index.tolist()
    if not registros["pais_destino"].isin(mercados).all():
        mercados.append(OTROS_MERCADOS)

    participacion = registros.groupby("tipo_flor")["volumen_kg"].sum() / registros["volumen_kg"].sum()
    flores = participacion[participacion >= participacion_min_flor].sort_values(ascending=False).index.tolist()
    if not registros["tipo_flor"].isin(flores).all():
        flores.append(OTRAS_FLORES)
    return mercados, flores


def agrupar_mercado(paises, mercados):
    return paises.where(paises.isin(mercados), OTROS_MERCADOS)


def agrupar_flor(tipos, flores):
    return tipos.where(tipos.isin(flores), OTRAS_FLORES)


def series_mensuales(registros, mercados, flores):
    """Panel con una fila por (flor, mercado, mes): volumen, valor y precio por kg."""
    datos = registros.assign(
        mercado=agrupar_mercado(registros["pais_destino"], mercados),
        flor=agrupar_flor(registros["tipo_flor"], flores),
        periodo=registros["fecha_despacho"].dt.to_period("M").dt.to_timestamp(),
    )
    agregado = datos.groupby(["flor", "mercado", "periodo"]).agg(
        volumen_kg=("volumen_kg", "sum"),
        valor_usd=("valor_fob_usd", "sum"),
    )
    # Los meses sin despachos no existen en los registros: se completan con 0
    periodos = pd.date_range(datos["periodo"].min(), datos["periodo"].max(), freq="MS")
    indice = pd.MultiIndex.from_product([flores, mercados, periodos], names=["flor", "mercado", "periodo"])
    panel = agregado.reindex(indice, fill_value=0).reset_index()
    panel["precio_kg"] = panel["valor_usd"] / panel["volumen_kg"].replace(0, np.nan)
    return panel
