from config import db
from models.base import BaseModel


class InventarioFinca(BaseModel):
    """Stock y cosechas de la finca. Se compara con los pronósticos; nunca se entrena."""

    __tablename__ = "inventario_finca"

    ESTADOS = ("en_cultivo", "cosechado", "en_cuarto_frio", "reservado", "despachado", "descartado")

    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    codigo_lote = db.Column(db.String(50))
    bloque = db.Column(db.String(50))
    tipo_flor = db.Column(db.String(50), nullable=False)
    variedad = db.Column(db.String(80))
    color = db.Column(db.String(40))
    grado_calidad = db.Column(db.String(30))
    longitud_tallo_cm = db.Column(db.SmallInteger)
    stock_tallos = db.Column(db.Integer)
    stock_kg = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(db.Enum(*ESTADOS), nullable=False, default="en_cultivo")
    fecha_cosecha = db.Column(db.Date, nullable=False)
    fecha_salida_desde = db.Column(db.Date, nullable=False)
    fecha_salida_hasta = db.Column(db.Date, nullable=False)
    vida_util_dias = db.Column(db.SmallInteger)
    costo_produccion_usd_kg = db.Column(db.Numeric(10, 2))
    precio_minimo_usd_kg = db.Column(db.Numeric(10, 2))
    observaciones = db.Column(db.String(500))
