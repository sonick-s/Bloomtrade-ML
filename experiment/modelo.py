"""
Paso 2 - Variables (features), modelo y métricas.

Modelo: regresión Ridge "global" (un solo modelo aprende de todas las series a la vez).
Predice log(volumen + 1) del mes a partir de:
  - qué serie es (flor y mercado)                 -> nivel base de cada serie
  - mes del año × mercado y mes del año × flor    -> temporadas (San Valentín, Día de la Mujer...)
  - tendencia general en años                     -> crecimiento del sector
  - volumen del mismo mes hace 1, 2 y 3 años      -> lag12, lag24, lag36
  - promedio de los 12 meses previos al lag12     -> nivel reciente de la serie (capta caídas
                                                     como la de Rusia o subidas como Kazajistán)
  - marcas de COVID (mar-may 2020) en esos lags   -> para no aprender esa caída como algo normal

Probamos también una tendencia por mercado: extrapolaba mal (Kazajistán "explotaba") y se quitó.

Todas las variables se conocen 12 meses antes, así que el modelo puede pronosticar hasta
12 meses hacia adelante sin usar datos del futuro.
"""
import numpy as np
import pandas as pd

from datos import FLORES, MERCADOS

HORIZONTE = 12
LAGS = (12, 24, 36)
INICIO = pd.Timestamp("2018-01-01")
COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-05-01"))


# --------------------------------------------------------------------------- features

def agregar_lags(panel):
    """Agrega columnas de historia por serie. Las filas futuras (volumen NaN) también las reciben."""
    panel = panel.sort_values(["flor", "mercado", "periodo"]).copy()
    panel["y"] = np.log1p(panel["volumen_kg"])
    grupos = panel.groupby(["flor", "mercado"])["y"]
    for lag in LAGS:
        panel[f"lag{lag}"] = grupos.shift(lag)
    panel["nivel12"] = grupos.transform(lambda s: s.shift(12).rolling(12).mean())
    return panel


COLUMNAS_HISTORIA = [*(f"lag{lag}" for lag in LAGS), "nivel12"]


def _es_covid(fechas):
    return ((fechas >= COVID[0]) & (fechas <= COVID[1])).astype(float)


def matriz_volumen(panel):
    fechas = panel["periodo"]
    años = ((fechas - INICIO).dt.days / 365.25).to_numpy()
    columnas = [
        *_one_hot(panel["flor"] + "|" + panel["mercado"], [f"{f}|{m}" for f in FLORES for m in MERCADOS]),
        *_estacionalidad(panel),
        años,
        *(_es_covid(fechas - pd.DateOffset(months=lag)).to_numpy() for lag in LAGS),
        *(panel[col].to_numpy() for col in COLUMNAS_HISTORIA),
    ]
    return np.column_stack(columnas)


def matriz_precio(panel):
    """El precio se modela más simple: nivel de la serie, temporada y tendencia."""
    años = ((panel["periodo"] - INICIO).dt.days / 365.25).to_numpy()
    columnas = [
        *_one_hot(panel["flor"] + "|" + panel["mercado"], [f"{f}|{m}" for f in FLORES for m in MERCADOS]),
        *_estacionalidad(panel),
        años,
        *(años * c for c in _one_hot(panel["mercado"], MERCADOS)),
    ]
    return np.column_stack(columnas)


def _estacionalidad(panel):
    meses = panel["periodo"].dt.month
    columnas = []
    for valores, categorias in ((panel["mercado"], MERCADOS), (panel["flor"], FLORES)):
        for categoria in _one_hot(valores, categorias):
            for mes in range(1, 13):
                columnas.append(categoria * (meses == mes).to_numpy())
    return columnas


def _one_hot(valores, categorias):
    return [(valores == c).to_numpy(dtype=float) for c in categorias]


# --------------------------------------------------------------------------- Ridge

def ajustar_ridge(X, y, alpha):
    """
    Regresión Ridge: mínimos cuadrados con una penalización alpha que evita coeficientes extremos.
    Resuelve (Zᵀ Z + alpha·I) β = Zᵀ (y - media), con Z = X estandarizada.
    """
    media, desv = X.mean(axis=0), X.std(axis=0)
    desv[desv == 0] = 1.0
    Z = (X - media) / desv
    y_media = y.mean()
    beta = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y_media))
    return {"media": media, "desv": desv, "beta": beta, "intercepto": y_media}


def predecir_ridge(modelo, X):
    return ((X - modelo["media"]) / modelo["desv"]) @ modelo["beta"] + modelo["intercepto"]


# --------------------------------------------------------------------------- entrenar y predecir

def entrenar_y_predecir(historia, futuro, alpha):
    """
    Entrena con 'historia' (meses conocidos) y predice volumen y precio para 'futuro'.
    'futuro' son filas (flor, mercado, periodo) de los meses a pronosticar.
    """
    panel = agregar_lags(pd.concat([historia, futuro.assign(volumen_kg=np.nan)], ignore_index=True))
    es_futuro = panel["periodo"] > historia["periodo"].max()
    entrenable = ~es_futuro & panel[COLUMNAS_HISTORIA].notna().all(axis=1)

    X = matriz_volumen(panel)
    m_vol = ajustar_ridge(X[entrenable], panel.loc[entrenable, "y"].to_numpy(), alpha)
    pred = panel.loc[es_futuro, ["flor", "mercado", "periodo"]].copy()
    pred["volumen_pred"] = np.clip(np.expm1(predecir_ridge(m_vol, X[es_futuro])), 0, None)

    con_precio = historia["volumen_kg"] > 0
    Xp = matriz_precio(historia[con_precio])
    m_precio = ajustar_ridge(Xp, np.log(historia.loc[con_precio, "precio_kg"].to_numpy()), alpha)
    pred["precio_pred"] = np.exp(predecir_ridge(m_precio, matriz_precio(pred)))
    return pred.reset_index(drop=True)


def ingenuo_estacional(historia, futuro):
    """Línea base: 'este mes vende lo mismo que el mismo mes del año pasado'."""
    hace_un_año = historia.assign(periodo=historia["periodo"] + pd.DateOffset(months=12))
    columnas = ["flor", "mercado", "periodo", "volumen_kg"]
    return futuro.merge(hace_un_año[columnas], on=["flor", "mercado", "periodo"], how="left").rename(
        columns={"volumen_kg": "base_pred"}
    )


def meses_futuros(ultimo_mes, horizonte=HORIZONTE):
    periodos = pd.date_range(ultimo_mes + pd.DateOffset(months=1), periods=horizonte, freq="MS")
    indice = pd.MultiIndex.from_product([FLORES, MERCADOS, periodos], names=["flor", "mercado", "periodo"])
    return indice.to_frame(index=False)


# --------------------------------------------------------------------------- métricas

def wape(real, pred):
    """
    Error porcentual absoluto ponderado: suma de errores / suma de lo real.
    Se usa en vez del MAPE porque hay meses con 0 kg, donde el MAPE se dispara.
    """
    real, pred = np.asarray(real, dtype=float), np.asarray(pred, dtype=float)
    total = np.abs(real).sum()
    return np.abs(real - pred).sum() / total if total else float("nan")  # nan: no hubo ventas que comparar
