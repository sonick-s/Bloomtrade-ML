from config import db
from models.base import BaseModel


class Dataset(BaseModel):
    """Cada CSV cargado. 'mercado' alimenta el entrenamiento; 'interno' es la data de la finca."""

    __tablename__ = "datasets"

    TIPOS = ("mercado", "interno")
    ORIGENES = ("base", "usuario")
    ESTADOS = ("pendiente", "validado", "con_errores")

    nombre = db.Column(db.String(150), nullable=False)
    archivo_original = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.Enum(*TIPOS), nullable=False, default="mercado")
    origen = db.Column(db.Enum(*ORIGENES), nullable=False, default="usuario")
    filas = db.Column(db.Integer, nullable=False, default=0)
    fecha_min = db.Column(db.Date)
    fecha_max = db.Column(db.Date)
    hash_sha256 = db.Column(db.CHAR(64), nullable=False, unique=True)
    estado = db.Column(db.Enum(*ESTADOS), nullable=False, default="pendiente")
    errores = db.Column(db.JSON)
