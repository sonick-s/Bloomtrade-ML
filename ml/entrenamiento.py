"""
Pipeline de entrenamiento:
  1. Agrupa los registros en series mensuales.
  2. Elige alpha y si corregir el sesgo con un año de validación (entrena hasta 24 meses
     antes del final y compara contra los 12 meses siguientes).
  3. Mide el error en el último año, que el modelo no ve (test), en varios niveles.
  4. Reentrena con todo y pronostica los próximos 12 meses con bandas de error.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ml.pronosticador import HORIZONTE, Pronosticador
from ml.series import COLUMNAS_REQUERIDAS, agrupar_mercado, elegir_grupos, series_mensuales

ALPHAS = (3, 10, 30, 100, 300, 1000)
CORRECCIONES = (False, True)
CLAVES = ["flor", "mercado", "periodo"]


class DatosInsuficientes(ValueError):
    pass


@dataclass
class Resultado:
    pronosticador: Pronosticador
    pronostico: pd.DataFrame
    metricas: dict
    parametros: dict


def entrenar(registros):
    """registros: DataFrame con COLUMNAS_REQUERIDAS (y opcionalmente tiempo_transito_dias)."""
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in registros.columns]
    if faltantes:
        raise DatosInsuficientes(f"Faltan columnas: {', '.join(faltantes)}")
    registros = registros.assign(fecha_despacho=pd.to_datetime(registros["fecha_despacho"]))

    mercados, flores = elegir_grupos(registros)
    panel = series_mensuales(registros, mercados, flores)
    lags = _lags_posibles(panel["periodo"].nunique())

    ultimo = panel["periodo"].max()
    corte_test = ultimo - pd.DateOffset(months=HORIZONTE)
    corte_validacion = corte_test - pd.DateOffset(months=HORIZONTE)

    # Hiperparámetros: se prueban todas las combinaciones y gana la de menor error en validación
    errores_validacion = {
        (alpha, corregir): wape(*_real_y_pred(_evaluar(panel, corte_validacion, mercados, flores, lags, alpha, corregir)))
        for alpha in ALPHAS
        for corregir in CORRECCIONES
    }
    alpha, corregir = min(errores_validacion, key=errores_validacion.get)

    test = _evaluar(panel, corte_test, mercados, flores, lags, alpha, corregir)
    metricas = _metricas(test)
    metricas.update(
        alpha=alpha,
        corregir_sesgo=corregir,
        errores_validacion={f"alpha={a} corregir={c}": e for (a, c), e in errores_validacion.items()},
    )

    pronosticador = Pronosticador(mercados, flores, lags, alpha, corregir).ajustar(panel)
    pronostico = _con_bandas(pronosticador.predecir(), metricas["por_serie"])

    parametros = {
        "mercados": mercados,
        "flores": flores,
        "lags": list(lags),
        "horizonte": HORIZONTE,
        "inicio": f"{panel['periodo'].min():%Y-%m-%d}",
        "ultimo_mes": f"{ultimo:%Y-%m-%d}",
        "corte_test": f"{corte_test:%Y-%m-%d}",
        "registros": int(len(registros)),
        "factor_sesgo": round(pronosticador.factor_sesgo, 4),
        "transito_dias": _transito_por_mercado(registros, mercados),
    }
    return Resultado(pronosticador, pronostico, metricas, parametros)


def wape(real, pred):
    """Suma de errores / suma real. Se usa en vez del MAPE porque hay meses con 0 kg."""
    real, pred = np.asarray(real, dtype=float), np.nan_to_num(np.asarray(pred, dtype=float))
    total = np.abs(real).sum()
    return float(np.abs(real - pred).sum() / total) if total else None


# --------------------------------------------------------------------------- internos

def _lags_posibles(meses):
    """Con menos historia se usan menos lags. Hacen falta 12 meses de validación + 12 de test."""
    if meses >= 72:
        return (12, 24, 36)
    if meses >= 60:
        return (12, 24)
    raise DatosInsuficientes(f"Se necesitan al menos 60 meses de historia (5 años); hay {meses}")


def _evaluar(panel, corte, mercados, flores, lags, alpha, corregir):
    """Entrena hasta 'corte' y compara los 12 meses siguientes con lo real y con la línea base."""
    historia = panel[panel["periodo"] <= corte]
    pred = Pronosticador(mercados, flores, lags, alpha, corregir).ajustar(historia).predecir()

    # Línea base: "este mes vende lo mismo que el mismo mes del año pasado"
    hace_un_año = historia.assign(periodo=historia["periodo"] + pd.DateOffset(months=12))
    base = hace_un_año[[*CLAVES, "volumen_kg"]].rename(columns={"volumen_kg": "base_pred"})
    return (
        pred.merge(base, on=CLAVES, how="left")
        .merge(panel[[*CLAVES, "volumen_kg", "precio_kg"]], on=CLAVES)
    )


def _real_y_pred(test):
    return test["volumen_kg"], test["volumen_pred"]


def _metricas(test):
    """Error en distintos niveles de agregación: entre más agregado, más confiable."""
    test = test.assign(serie=test["flor"] + "|" + test["mercado"])
    niveles = {
        "serie_mes": ["serie", "periodo"],
        "mercado_mes": ["mercado", "periodo"],
        "total_mes": ["periodo"],
        "mercado_anio": ["mercado"],
    }
    metricas = {}
    for nombre, claves in niveles.items():
        agregado = test.groupby(claves)[["volumen_kg", "volumen_pred", "base_pred"]].sum()
        metricas[f"wape_{nombre}"] = wape(agregado["volumen_kg"], agregado["volumen_pred"])
        metricas[f"wape_base_{nombre}"] = wape(agregado["volumen_kg"], agregado["base_pred"])

    total_real, total_pred = test["volumen_kg"].sum(), test["volumen_pred"].sum()
    metricas["error_total_anio"] = float(abs(total_pred / total_real - 1)) if total_real else None

    con_venta = test["volumen_kg"] > 0
    metricas["wape_precio"] = wape(test.loc[con_venta, "precio_kg"], test.loc[con_venta, "precio_pred"])
    metricas["por_serie"] = {
        serie: wape(g["volumen_kg"], g["volumen_pred"]) for serie, g in test.groupby("serie")
    }
    # Métrica principal para comparar modelos (la que decide si se activa)
    metricas["wape"] = metricas["wape_serie_mes"]
    return metricas


def _con_bandas(pronostico, error_por_serie):
    """Banda de error: pronóstico ± el error que tuvo esa serie en el test (máximo ±100%)."""
    error = (pronostico["flor"] + "|" + pronostico["mercado"]).map(error_por_serie).fillna(1.0).clip(upper=1.0)
    return pronostico.assign(
        limite_inf=(pronostico["volumen_pred"] * (1 - error)).clip(lower=0),
        limite_sup=pronostico["volumen_pred"] * (1 + error),
    )


def _transito_por_mercado(registros, mercados):
    """Días promedio de tránsito por mercado: sirve para descartar destinos según la vida útil."""
    if "tiempo_transito_dias" not in registros.columns:
        return {}
    transito = registros.assign(mercado=agrupar_mercado(registros["pais_destino"], mercados))
    promedio = transito.groupby("mercado")["tiempo_transito_dias"].mean().dropna()
    return {mercado: round(float(dias), 1) for mercado, dias in promedio.items()}
