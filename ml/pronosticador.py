"""
Modelo de pronóstico: un solo modelo Ridge "global" que aprende de todas las series a la vez.

Volumen: predice log(volumen + 1) del mes con estas variables:
  - qué serie es (flor y mercado)                 -> nivel base de cada serie
  - mes del año × mercado y mes del año × flor    -> temporadas (San Valentín, Día de la Mujer...)
  - volumen del mismo mes hace 1, 2 y 3 años      -> lags
  - promedio de los 12 meses previos al lag12     -> nivel reciente de la serie
  - marcas de COVID (mar-may 2020) en esos lags   -> para no aprender esa caída como algo normal
No lleva variable de tendencia: los lags ya traen el nivel reciente de cada serie y la tendencia
lo extrapolaba de más (con alpha bajo sobrestimaba el total en +50-70%).
Al volver de log a kilos el modelo puede subestimar el total (desigualdad de Jensen). Por eso
existe una corrección de sesgo opcional (factor global real / ajustado, "smearing" de Duan).
Si conviene o no depende de los datos: la decide la validación junto con alpha.

Precio: Ridge sobre log(precio) con nivel de la serie, temporada y tendencia por mercado.

Todas las variables se conocen 12 meses antes, así que se pronostica hasta 12 meses sin
usar información del futuro.
"""
import numpy as np
import pandas as pd

from ml import ridge

HORIZONTE = 12
COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-05-01"))


class Pronosticador:
    def __init__(self, mercados, flores, lags, alpha, corregir_sesgo):
        self.mercados = list(mercados)
        self.flores = list(flores)
        self.lags = tuple(lags)
        self.alpha = alpha
        self.corregir_sesgo = corregir_sesgo
        self.columnas_historia = [*(f"lag{lag}" for lag in self.lags), "nivel12"]

    # ------------------------------------------------------------------ API

    def ajustar(self, historia):
        """Entrena con el panel histórico (flor, mercado, periodo, volumen_kg, precio_kg)."""
        self.historia = historia[["flor", "mercado", "periodo", "volumen_kg", "precio_kg"]].copy()
        self.inicio = historia["periodo"].min()
        self.ultimo_mes = historia["periodo"].max()

        panel = self._agregar_lags(self.historia)
        entrenable = panel[self.columnas_historia].notna().all(axis=1)
        X = self._matriz_volumen(panel[entrenable])
        self.modelo_volumen = ridge.ajustar(X, panel.loc[entrenable, "y"].to_numpy(), self.alpha)

        self.factor_sesgo = 1.0
        if self.corregir_sesgo:
            ajustado = np.clip(np.expm1(ridge.predecir(self.modelo_volumen, X)), 0, None).sum()
            if ajustado > 0:
                self.factor_sesgo = float(panel.loc[entrenable, "volumen_kg"].sum() / ajustado)

        con_precio = historia["volumen_kg"] > 0
        self.modelo_precio = ridge.ajustar(
            self._matriz_precio(historia[con_precio]),
            np.log(historia.loc[con_precio, "precio_kg"].to_numpy()),
            self.alpha,
        )
        return self

    def predecir(self, horizonte=HORIZONTE):
        """Pronóstico de los próximos meses: volumen_pred y precio_pred por (flor, mercado, periodo)."""
        futuro = self.meses_futuros(horizonte)
        panel = self._agregar_lags(pd.concat([self.historia, futuro], ignore_index=True))
        es_futuro = panel["periodo"] > self.ultimo_mes
        filas = panel.loc[es_futuro, ["flor", "mercado", "periodo"]].reset_index(drop=True)

        log_volumen = ridge.predecir(self.modelo_volumen, self._matriz_volumen(panel[es_futuro]))
        filas["volumen_pred"] = np.clip(np.expm1(log_volumen), 0, None) * self.factor_sesgo
        filas["precio_pred"] = np.exp(ridge.predecir(self.modelo_precio, self._matriz_precio(filas)))
        return filas

    def meses_futuros(self, horizonte=HORIZONTE):
        periodos = pd.date_range(self.ultimo_mes + pd.DateOffset(months=1), periods=horizonte, freq="MS")
        indice = pd.MultiIndex.from_product([self.flores, self.mercados, periodos], names=["flor", "mercado", "periodo"])
        return indice.to_frame(index=False)

    # ------------------------------------------------------------------ variables

    def _agregar_lags(self, panel):
        panel = panel.sort_values(["flor", "mercado", "periodo"]).copy()
        panel["y"] = np.log1p(panel["volumen_kg"])
        grupos = panel.groupby(["flor", "mercado"])["y"]
        for lag in self.lags:
            panel[f"lag{lag}"] = grupos.shift(lag)
        panel["nivel12"] = grupos.transform(lambda s: s.shift(12).rolling(12).mean())
        return panel

    def _matriz_volumen(self, panel):
        fechas = panel["periodo"]
        columnas = [
            *self._series(panel),
            *self._estacionalidad(panel),
            *(self._es_covid(fechas - pd.DateOffset(months=lag)) for lag in self.lags),
            *(panel[col].to_numpy() for col in self.columnas_historia),
        ]
        return np.column_stack(columnas)

    def _matriz_precio(self, panel):
        años = self._años(panel["periodo"])
        columnas = [
            *self._series(panel),
            *self._estacionalidad(panel),
            años,
            *(años * c for c in _one_hot(panel["mercado"], self.mercados)),
        ]
        return np.column_stack(columnas)

    def _series(self, panel):
        claves = [f"{f}|{m}" for f in self.flores for m in self.mercados]
        return _one_hot(panel["flor"] + "|" + panel["mercado"], claves)

    def _estacionalidad(self, panel):
        meses = panel["periodo"].dt.month.to_numpy()
        columnas = []
        for valores, categorias in ((panel["mercado"], self.mercados), (panel["flor"], self.flores)):
            for categoria in _one_hot(valores, categorias):
                columnas.extend(categoria * (meses == mes) for mes in range(1, 13))
        return columnas

    def _años(self, fechas):
        return ((fechas - self.inicio).dt.days / 365.25).to_numpy()

    @staticmethod
    def _es_covid(fechas):
        return ((fechas >= COVID[0]) & (fechas <= COVID[1])).to_numpy(dtype=float)


def _one_hot(valores, categorias):
    return [(valores == c).to_numpy(dtype=float) for c in categorias]
