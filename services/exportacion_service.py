from models import Exportacion
from services.base_service import BaseService
from services.dataset_service import dataset_service


class ExportacionService(BaseService):
    model = Exportacion
    entity_name = "Exportación"

    def validate(self, data, current=None):
        # Las exportaciones solo pertenecen a datasets de mercado (datos de entrenamiento)
        if "dataset_id" in data:
            dataset_service.get_of_type(data["dataset_id"], "mercado")


exportacion_service = ExportacionService()
