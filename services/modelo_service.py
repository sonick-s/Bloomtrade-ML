from config import db
from config.global_exceptions import NotFoundException
from models import Modelo
from services.base_service import BaseService
from services.dataset_service import dataset_service


class ModeloService(BaseService):
    model = Modelo
    entity_name = "Modelo"

    def create(self, data):
        data = dict(data)
        dataset_ids = data.pop("dataset_ids", [])
        modelo = Modelo(**data)
        modelo.datasets = self._training_datasets(dataset_ids)
        db.session.add(modelo)
        self.commit()
        return modelo

    def update(self, entity_id, data):
        data = dict(data)
        modelo = self.get(entity_id)
        if "dataset_ids" in data:
            modelo.datasets = self._training_datasets(data.pop("dataset_ids"))
        for field, value in data.items():
            setattr(modelo, field, value)
        self.commit()
        return modelo

    def get_active(self):
        modelo = db.session.scalar(db.select(Modelo).where(Modelo.activo.is_(True)))
        if modelo is None:
            raise NotFoundException("No hay ningún modelo activo")
        return modelo

    def activate(self, entity_id):
        """Deja este modelo como el único activo (lo usa la predicción y el dashboard)."""
        modelo = self.get(entity_id)
        # Primero se desactivan todos para respetar la restricción de un solo activo
        db.session.execute(db.update(Modelo).where(Modelo.id != modelo.id).values(activo=False))
        db.session.flush()
        modelo.activo = True
        self.commit()
        return modelo

    @staticmethod
    def _training_datasets(dataset_ids):
        # Solo datasets de mercado; los internos de la finca nunca se entrenan
        return [dataset_service.get_of_type(dataset_id, "mercado") for dataset_id in set(dataset_ids)]


modelo_service = ModeloService()
