"""
Experimento de pronóstico de demanda de flores.

    python experiment/run.py

1. Prepara las series mensuales desde el CSV                    (datos.py)
2. Elige el parámetro alpha con un año de validación            (modelo.py)
3. Mide el error en el último año, que el modelo no ve (test)   (modelo.py)
4. Reentrena con todo y pronostica los próximos 12 meses
5. Genera experiment/dashboard.html                              (dashboard.py)
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd

import dashboard
from datos import cargar, series_mensuales
from modelo import HORIZONTE, entrenar_y_predecir, ingenuo_estacional, meses_futuros, wape

ALPHAS = [1, 3, 10, 30, 100, 300, 1000, 3000]
SALIDA = Path(__file__).resolve().parent / "dashboard.html"


def evaluar(panel, corte, alpha):
    """Entrena con los meses <= corte y compara contra los 12 meses siguientes reales."""
    historia = panel[panel["periodo"] <= corte]
    futuro = meses_futuros(corte)
    claves = ["flor", "mercado", "periodo"]
    pred = entrenar_y_predecir(historia, futuro, alpha).merge(ingenuo_estacional(historia, futuro), on=claves)
    return pred.merge(panel[[*claves, "volumen_kg", "precio_kg"]], on=claves)


def piso_de_error(test, semillas=range(100, 115)):
    """
    Error que ningún modelo puede evitar (ruido de los envíos individuales).
    Solo se puede medir porque los datos son sintéticos: se generan otros datasets con el
    mismo proceso y semillas distintas; su promedio aproxima la demanda "esperada" real.
    """
    ruta = Path(__file__).resolve().parent.parent / "scripts" / "generate_ecuador_exports.py"
    spec = importlib.util.spec_from_file_location("generador", ruta)
    generador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generador)

    claves = ["flor", "mercado", "periodo"]
    simulaciones = []
    for semilla in semillas:
        df = pd.DataFrame(generador.generate(10000, semilla))
        df["Fecha_Despacho"] = pd.to_datetime(df["Fecha_Despacho"])
        simulaciones.append(series_mensuales(df).set_index(claves)["volumen_kg"])
    esperado = pd.concat(simulaciones, axis=1).mean(axis=1).rename("esperado").reset_index()
    comparado = test.merge(esperado, on=claves)
    return wape(comparado["volumen_kg"], comparado["esperado"])


def elegir_alpha(panel, corte_validacion):
    errores = {a: wape(r["volumen_kg"], r["volumen_pred"])
               for a in ALPHAS
               for r in [evaluar(panel, corte_validacion, a)]}
    return min(errores, key=errores.get), errores


def main():
    panel = series_mensuales(cargar())
    ultimo = panel["periodo"].max()
    corte_test = ultimo - pd.DateOffset(months=HORIZONTE)
    corte_validacion = corte_test - pd.DateOffset(months=HORIZONTE)

    alpha, errores_validacion = elegir_alpha(panel, corte_validacion)
    test = evaluar(panel, corte_test, alpha)
    pronostico = entrenar_y_predecir(panel, meses_futuros(ultimo), alpha)

    con_venta = test["volumen_kg"] > 0
    resumen = {
        "alpha": alpha,
        "errores_validacion": errores_validacion,
        "wape_modelo": wape(test["volumen_kg"], test["volumen_pred"]),
        "wape_base": wape(test["volumen_kg"], test["base_pred"]),
        "wape_precio": wape(test.loc[con_venta, "precio_kg"], test.loc[con_venta, "precio_pred"]),
        "piso_error": piso_de_error(test),
        "ultimo_mes": ultimo,
        "corte_test": corte_test,
    }

    print(f"Datos: {panel['periodo'].min():%Y-%m} a {ultimo:%Y-%m} · {panel.groupby(['flor', 'mercado']).ngroups} series")
    print("Validación (WAPE por alpha):", {a: f"{e:.1%}" for a, e in errores_validacion.items()})
    print(f"alpha elegido: {alpha}")
    print(f"Test {corte_test + pd.DateOffset(months=1):%Y-%m} a {ultimo:%Y-%m}: "
          f"WAPE modelo {resumen['wape_modelo']:.1%} · línea base {resumen['wape_base']:.1%} · "
          f"precio {resumen['wape_precio']:.1%} · piso inevitable {resumen['piso_error']:.1%}")

    if "--sin-dashboard" not in sys.argv:
        SALIDA.write_text(dashboard.construir(panel, test, pronostico, resumen), encoding="utf-8")
        print(f"Dashboard: {SALIDA}")
    return panel, test, pronostico, resumen


if __name__ == "__main__":
    main()
