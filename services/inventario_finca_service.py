from config.global_exceptions import BadRequestException
from models import InventarioFinca
from services.base_service import BaseService
from services.dataset_service import dataset_service


class InventarioFincaService(BaseService):
    model = InventarioFinca
    entity_name = "Lote de inventario"

    def validate(self, data, current=None):
        # El inventario solo pertenece a datasets internos (nunca se entrenan)
        if "dataset_id" in data:
            dataset_service.get_of_type(data["dataset_id"], "interno")

        desde = self.merged(data, current, "fecha_salida_desde")
        hasta = self.merged(data, current, "fecha_salida_hasta")
        if desde and hasta and hasta < desde:
            raise BadRequestException("fecha_salida_hasta no puede ser anterior a fecha_salida_desde")


inventario_finca_service = InventarioFincaService()
