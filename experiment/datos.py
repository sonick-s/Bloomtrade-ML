"""
Paso 1 - Preparar los datos.

Convierte los envíos individuales del CSV en series de tiempo mensuales:
una serie por cada combinación (flor, mercado) con el volumen y el valor de cada mes.
"""
from pathlib import Path

import numpy as np
import pandas as pd

CSV = Path(__file__).resolve().parent.parent / "docs" / "exportaciones_ecuador_flores.csv"

# Con 10.000 registros, los países pequeños tienen muy pocos datos por mes.
# Se modelan los mercados principales y el resto se agrupa en "Otros".
MERCADOS = ["Estados Unidos", "Kazajistán", "Países Bajos", "Rusia", "Canadá", "Italia", "Otros"]
# Igual con las flores: las de menor volumen se agrupan en "Otras flores".
FLORES = ["Rosas", "Flores de verano", "Otras flores"]


def cargar(path=CSV):
    return pd.read_csv(path, encoding="utf-8-sig", parse_dates=["Fecha_Despacho"])


def series_mensuales(df):
    """Devuelve un panel: una fila por (flor, mercado, mes) con volumen, valor y precio."""
    df = df.assign(
        mercado=df["Pais_Destino"].where(df["Pais_Destino"].isin(MERCADOS), "Otros"),
        flor=df["Tipo_Flor"].where(df["Tipo_Flor"].isin(FLORES), "Otras flores"),
        periodo=df["Fecha_Despacho"].dt.to_period("M").dt.to_timestamp(),
    )
    agregado = df.groupby(["flor", "mercado", "periodo"]).agg(
        volumen_kg=("Volumen_Kg", "sum"),
        valor_usd=("Valor_FOB_USD", "sum"),
    )

    # Los meses sin despachos no aparecen en el CSV: se completan con 0
    periodos = pd.date_range(df["periodo"].min(), df["periodo"].max(), freq="MS")
    indice = pd.MultiIndex.from_product([FLORES, MERCADOS, periodos], names=["flor", "mercado", "periodo"])
    panel = agregado.reindex(indice, fill_value=0).reset_index()

    panel["precio_kg"] = panel["valor_usd"] / panel["volumen_kg"].replace(0, np.nan)
    return panel
