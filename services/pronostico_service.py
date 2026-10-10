from config.global_exceptions import BadRequestException
from models import Pronostico
from services.base_service import BaseService
from services.modelo_service import modelo_service


class PronosticoService(BaseService):
    model = Pronostico
    entity_name = "Pronóstico"

    def validate(self, data, current=None):
        if "modelo_id" in data:
            modelo_service.get(data["modelo_id"])

        pred = self.merged(data, current, "volumen_kg_pred")
        inf = self.merged(data, current, "limite_inf")
        sup = self.merged(data, current, "limite_sup")
        if inf is not None and pred is not None and inf > pred:
            raise BadRequestException("limite_inf no puede ser mayor que volumen_kg_pred")
        if sup is not None and pred is not None and sup < pred:
            raise BadRequestException("limite_sup no puede ser menor que volumen_kg_pred")


pronostico_service = PronosticoService()
