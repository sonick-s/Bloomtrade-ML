from config import db
from models.base import BaseModel

# Con qué datasets se entrenó cada modelo (trazabilidad)
modelo_datasets = db.Table(
    "modelo_datasets",
    db.Column("modelo_id", db.Integer, db.ForeignKey("modelos.id", ondelete="CASCADE"), primary_key=True),
    db.Column("dataset_id", db.Integer, db.ForeignKey("datasets.id", ondelete="RESTRICT"), primary_key=True),
)


class Modelo(BaseModel):
    """Versión entrenada del modelo de pronóstico. El artefacto (.joblib) vive en disco."""

    __tablename__ = "modelos"

    version = db.Column(db.Integer, nullable=False, unique=True)
    algoritmo = db.Column(db.String(50), nullable=False)
    ruta_artefacto = db.Column(db.String(255), nullable=False)
    parametros = db.Column(db.JSON)
    metricas = db.Column(db.JSON)
    activo = db.Column(db.Boolean, nullable=False, default=False)

    datasets = db.relationship("Dataset", secondary=modelo_datasets, lazy="selectin")

    @property
    def dataset_ids(self):
        return [dataset.id for dataset in self.datasets]
