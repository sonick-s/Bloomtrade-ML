from controllers.crud import crud_blueprint
from services.pronostico_service import pronostico_service
from views.pronostico_schema import PronosticoPageSchema, PronosticoQuerySchema, PronosticoSchema

blp = crud_blueprint(
    name="pronosticos",
    description="Predicciones mensuales por modelo, flor y país",
    service=pronostico_service,
    schema=PronosticoSchema,
    query_schema=PronosticoQuerySchema,
    page_schema=PronosticoPageSchema,
    label="pronósticos",
)
