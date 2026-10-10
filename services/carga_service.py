"""
Carga de un CSV a la base de datos: valida, versiona (tabla datasets) e inserta todas las filas.
  tipo 'mercado' -> exportaciones      (datos de entrenamiento)
  tipo 'interno' -> inventario_finca   (información de la finca, nunca se entrena)
"""
import hashlib
import io
import unicodedata

import pandas as pd

from config import db
from config.global_exceptions import BadRequestException, ConflictException
from models import Dataset, Exportacion, InventarioFinca

LOTE_INSERCION = 1000
MAX_ERRORES_DETALLE = 10

ESQUEMAS = {
    "mercado": {
        "modelo": Exportacion,
        "requeridas": ["fecha_despacho", "tipo_flor", "pais_destino", "volumen_kg", "valor_fob_usd"],
        "opcionales": ["temporada", "exportador", "tamano_empresa", "provincia_origen", "aeropuerto_salida",
                       "subpartida_nandina", "tiempo_transito_dias", "precio_fob_usd_kg"],
        "fechas": ["fecha_despacho"],
        "numeros": ["volumen_kg", "valor_fob_usd", "precio_fob_usd_kg", "tiempo_transito_dias"],
        "fecha_rango": "fecha_despacho",
    },
    "interno": {
        "modelo": InventarioFinca,
        "requeridas": ["tipo_flor", "stock_kg", "fecha_cosecha", "fecha_salida_desde", "fecha_salida_hasta"],
        "opcionales": ["codigo_lote", "bloque", "variedad", "color", "grado_calidad", "longitud_tallo_cm",
                       "stock_tallos", "estado", "vida_util_dias", "costo_produccion_usd_kg",
                       "precio_minimo_usd_kg", "observaciones"],
        "fechas": ["fecha_cosecha", "fecha_salida_desde", "fecha_salida_hasta"],
        "numeros": ["stock_kg", "longitud_tallo_cm", "stock_tallos", "vida_util_dias",
                    "costo_produccion_usd_kg", "precio_minimo_usd_kg"],
        "fecha_rango": "fecha_salida_desde",
    },
}


def cargar_csv(archivo, nombre, tipo, origen="usuario"):
    contenido = archivo.read()
    if not contenido:
        raise BadRequestException("El archivo está vacío")

    hash_sha256 = hashlib.sha256(contenido).hexdigest()
    existente = db.session.scalar(db.select(Dataset).where(Dataset.hash_sha256 == hash_sha256))
    if existente:
        raise ConflictException(f"Este archivo ya fue cargado como el dataset {existente.id} ('{existente.nombre}')")

    esquema = ESQUEMAS[tipo]
    datos, errores = _leer_y_validar(contenido, esquema)

    dataset = Dataset(
        nombre=nombre,
        archivo_original=archivo.filename or "archivo.csv",
        tipo=tipo,
        origen=origen,
        hash_sha256=hash_sha256,
    )
    if errores:
        # Se guarda el intento con sus errores (sin filas) para que quede registro
        dataset.estado, dataset.errores, dataset.filas = "con_errores", errores, 0
        db.session.add(dataset)
        db.session.commit()
        return dataset

    columna_fecha = datos[esquema["fecha_rango"]]
    dataset.estado, dataset.filas = "validado", len(datos)
    dataset.fecha_min, dataset.fecha_max = columna_fecha.min().date(), columna_fecha.max().date()
    db.session.add(dataset)
    db.session.flush()  # obtiene dataset.id para las filas

    filas = _a_registros(datos.assign(dataset_id=dataset.id))
    for inicio in range(0, len(filas), LOTE_INSERCION):
        db.session.execute(db.insert(esquema["modelo"]), filas[inicio:inicio + LOTE_INSERCION])
    db.session.commit()
    return dataset


# --------------------------------------------------------------------------- validación

def _normalizar(nombre):
    """'Fecha Despacho ' -> 'fecha_despacho' (minúsculas, sin tildes, guiones bajos)."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return "_".join(sin_tildes.strip().lower().replace("-", " ").split())


def _leer_y_validar(contenido, esquema):
    try:
        datos = pd.read_csv(io.BytesIO(contenido), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except (UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise BadRequestException(f"No se pudo leer el CSV: {exc}") from exc
    datos.columns = [_normalizar(c) for c in datos.columns]

    faltantes = [c for c in esquema["requeridas"] if c not in datos.columns]
    if faltantes:
        return None, {"columnas_faltantes": faltantes, "columnas_recibidas": list(datos.columns)}
    if datos.empty:
        return None, {"mensaje": "El archivo no tiene filas"}

    columnas = [c for c in esquema["requeridas"] + esquema["opcionales"] if c in datos.columns]
    datos = datos[columnas].apply(lambda s: s.str.strip()).replace("", None)

    problemas = {}
    for col in esquema["requeridas"]:
        _registrar(problemas, f"{col} vacío", datos[col].isna())
    for col in (c for c in esquema["fechas"] if c in datos.columns):
        texto = datos[col]
        datos[col] = pd.to_datetime(texto, errors="coerce")
        _registrar(problemas, f"{col} no es una fecha válida", texto.notna() & datos[col].isna())
    for col in (c for c in esquema["numeros"] if c in datos.columns):
        texto = datos[col]
        datos[col] = pd.to_numeric(texto, errors="coerce")
        _registrar(problemas, f"{col} no es un número", texto.notna() & datos[col].isna())
        _registrar(problemas, f"{col} es negativo", datos[col] < 0)

    if "fecha_salida_hasta" in datos.columns:
        _registrar(problemas, "fecha_salida_hasta es anterior a fecha_salida_desde",
                   datos["fecha_salida_hasta"] < datos["fecha_salida_desde"])
    if "estado" in datos.columns:
        datos["estado"] = datos["estado"].fillna("en_cultivo")
        _registrar(problemas, f"estado no es uno de {', '.join(InventarioFinca.ESTADOS)}",
                   ~datos["estado"].isin(InventarioFinca.ESTADOS))

    if problemas:
        return None, {"filas_con_errores": problemas}
    return datos, None


def _registrar(problemas, descripcion, mascara):
    """Guarda cuántas filas tienen el problema y algunos números de fila (como en Excel: fila 2 = primer dato)."""
    mascara = mascara.fillna(False)
    if mascara.any():
        filas = (mascara[mascara].index + 2).tolist()
        problemas[descripcion] = {"cantidad": len(filas), "filas": filas[:MAX_ERRORES_DETALLE]}


def _a_registros(datos):
    """DataFrame -> lista de dicts con fechas de Python y None en vez de NaN (lo que espera el INSERT)."""
    datos = datos.copy()
    for col in datos.select_dtypes("datetime").columns:
        datos[col] = datos[col].dt.date
    return datos.astype(object).where(datos.notna(), None).to_dict("records")
