"""
Entrenamiento de un modelo nuevo con datos de la base:
  1. Lee las exportaciones de los datasets de mercado elegidos.
  2. Entrena (ml/entrenamiento.py) y guarda el artefacto en disco.
  3. Registra la versión en `modelos` (métricas, parámetros, datasets usados).
  4. Guarda sus pronósticos en `pronosticos` (inferencia por lotes).
  5. Si se pide, lo activa cuando mejora al modelo activo (campeón / retador).
"""
from pathlib import Path

import pandas as pd

from config import db
from config.global_exceptions import BadRequestException
from ml import artefactos
from ml.entrenamiento import DatosInsuficientes, entrenar
from models import Dataset, Exportacion, Modelo, Pronostico
from services.dataset_service import dataset_service
from services.modelo_service import modelo_service

ALGORITMO = "ridge-global"


def entrenar_modelo(dataset_ids=None, activar_si_mejora=True):
    datasets = _datasets_de_entrenamiento(dataset_ids)
    registros = _leer_registros([d.id for d in datasets])

    try:
        resultado = entrenar(registros)
    except DatosInsuficientes as exc:
        raise BadRequestException(str(exc)) from exc

    version = (db.session.scalar(db.select(db.func.max(Modelo.version))) or 0) + 1
    ruta = artefactos.guardar(resultado.pronosticador, version)
    try:
        modelo = Modelo(
            version=version,
            algoritmo=ALGORITMO,
            ruta_artefacto=ruta,
            parametros=resultado.parametros,
            metricas=resultado.metricas,
            datasets=datasets,
        )
        db.session.add(modelo)
        db.session.flush()
        db.session.execute(db.insert(Pronostico), _filas_pronostico(modelo.id, resultado.pronostico))
        modelo_service.commit()
    except Exception:
        db.session.rollback()
        Path(artefactos.CARPETA.parent.parent / ruta).unlink(missing_ok=True)
        raise

    campeon = _modelo_activo()
    activado = activar_si_mejora and _mejora(modelo, campeon)
    if activado:
        modelo_service.activate(modelo.id)
    return {
        "modelo": modelo,
        "activado": activado,
        "mensaje": _mensaje(modelo, campeon, activar_si_mejora, activado),
    }


# --------------------------------------------------------------------------- internos

def _datasets_de_entrenamiento(dataset_ids):
    """Los indicados, o todos los de mercado validados si no se indica ninguno."""
    if dataset_ids:
        datasets = [dataset_service.get_of_type(i, "mercado") for i in dict.fromkeys(dataset_ids)]
    else:
        datasets = db.session.scalars(
            db.select(Dataset).where(Dataset.tipo == "mercado", Dataset.estado == "validado")
        ).all()
    if not datasets:
        raise BadRequestException("No hay datasets de mercado para entrenar. Carga un CSV primero.")
    no_validos = [d.id for d in datasets if d.estado != "validado"]
    if no_validos:
        raise BadRequestException(f"Los datasets {no_validos} no están validados")
    return datasets


def _leer_registros(dataset_ids):
    columnas = [Exportacion.fecha_despacho, Exportacion.tipo_flor, Exportacion.pais_destino,
                Exportacion.volumen_kg, Exportacion.valor_fob_usd, Exportacion.tiempo_transito_dias]
    consulta = db.select(*columnas).where(Exportacion.dataset_id.in_(dataset_ids))
    registros = pd.read_sql(consulta, db.session.connection())
    for col in ("volumen_kg", "valor_fob_usd", "tiempo_transito_dias"):
        registros[col] = pd.to_numeric(registros[col])
    return registros


def _filas_pronostico(modelo_id, pronostico):
    return [
        {
            "modelo_id": modelo_id,
            "tipo_flor": fila.flor,
            "pais_destino": fila.mercado,
            "periodo": fila.periodo.date(),
            "volumen_kg_pred": round(float(fila.volumen_pred), 2),
            "precio_usd_kg_pred": round(float(fila.precio_pred), 2),
            "limite_inf": round(float(fila.limite_inf), 2),
            "limite_sup": round(float(fila.limite_sup), 2),
        }
        for fila in pronostico.itertuples()
    ]


def _modelo_activo():
    return db.session.scalar(db.select(Modelo).where(Modelo.activo.is_(True)))


def _mejora(retador, campeon):
    if campeon is None:
        return True
    return (retador.metricas or {}).get("wape", 1e9) <= (campeon.metricas or {}).get("wape", 1e9)


def _mensaje(modelo, campeon, activar_si_mejora, activado):
    error = modelo.metricas.get("wape")
    texto = f"Modelo v{modelo.version} entrenado (error {error:.1%})."
    if not activar_si_mejora:
        return texto + " No se activó (activación manual)."
    if campeon is None:
        return texto + " Se activó porque no había un modelo activo."
    error_campeon = campeon.metricas.get("wape")
    if activado:
        return texto + f" Se activó: mejora o iguala al v{campeon.version} ({error_campeon:.1%})."
    return texto + f" Queda inactivo: el v{campeon.version} activo tiene menor error ({error_campeon:.1%})."
