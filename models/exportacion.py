from config import db
from models.base import BaseModel


class Exportacion(BaseModel):
    """Registro de exportación del mercado (datos de entrenamiento)."""

    __tablename__ = "exportaciones"

    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    fecha_despacho = db.Column(db.Date, nullable=False)
    # Columnas calculadas por la base de datos a partir de fecha_despacho
    anio = db.Column(db.SmallInteger, db.Computed("YEAR(fecha_despacho)", persisted=True))
    mes = db.Column(db.SmallInteger, db.Computed("MONTH(fecha_despacho)", persisted=True))
    temporada = db.Column(db.String(30))
    exportador = db.Column(db.String(100))
    tamano_empresa = db.Column(db.String(20))
    provincia_origen = db.Column(db.String(50))
    aeropuerto_salida = db.Column(db.String(80))
    subpartida_nandina = db.Column(db.String(12))
    tipo_flor = db.Column(db.String(50), nullable=False)
    pais_destino = db.Column(db.String(80), nullable=False)
    tiempo_transito_dias = db.Column(db.SmallInteger)
    volumen_kg = db.Column(db.Numeric(12, 2), nullable=False)
    precio_fob_usd_kg = db.Column(db.Numeric(10, 2))
    valor_fob_usd = db.Column(db.Numeric(14, 2), nullable=False)
