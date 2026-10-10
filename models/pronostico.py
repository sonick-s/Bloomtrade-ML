from config import db
from models.base import BaseModel


class Pronostico(BaseModel):
    """Predicción mensual de un modelo para una flor y un país (periodo = primer día del mes)."""

    __tablename__ = "pronosticos"
    __table_args__ = (
        db.UniqueConstraint("modelo_id", "tipo_flor", "pais_destino", "periodo", name="uq_pronosticos_serie"),
    )

    modelo_id = db.Column(db.Integer, db.ForeignKey("modelos.id", ondelete="CASCADE"), nullable=False)
    tipo_flor = db.Column(db.String(50), nullable=False)
    pais_destino = db.Column(db.String(80), nullable=False)
    periodo = db.Column(db.Date, nullable=False)
    volumen_kg_pred = db.Column(db.Numeric(14, 2), nullable=False)
    limite_inf = db.Column(db.Numeric(14, 2))
    limite_sup = db.Column(db.Numeric(14, 2))
