from config import db
from config.global_exceptions import BadRequestException, ConflictException
from models import Dataset, Exportacion, InventarioFinca
from services.base_service import BaseService


class DatasetService(BaseService):
    model = Dataset
    entity_name = "Dataset"

    def get_of_type(self, dataset_id, tipo):
        """Devuelve el dataset si existe y es del tipo esperado ('mercado' o 'interno')."""
        dataset = self.get(dataset_id)
        if dataset.tipo != tipo:
            raise BadRequestException(f"El dataset {dataset_id} es de tipo '{dataset.tipo}', se esperaba '{tipo}'")
        return dataset

    def validate(self, data, current=None):
        fecha_min = self.merged(data, current, "fecha_min")
        fecha_max = self.merged(data, current, "fecha_max")
        if fecha_min and fecha_max and fecha_min > fecha_max:
            raise BadRequestException("fecha_min no puede ser posterior a fecha_max")

        tipo_cambia = current is not None and "tipo" in data and data["tipo"] != current.tipo
        if tipo_cambia and self._has_rows(current.id):
            raise ConflictException("No se puede cambiar el tipo de un dataset que ya tiene registros")

    @staticmethod
    def _has_rows(dataset_id):
        for model in (Exportacion, InventarioFinca):
            if db.session.scalar(db.select(model.id).where(model.dataset_id == dataset_id).limit(1)):
                return True
        return False


dataset_service = DatasetService()
