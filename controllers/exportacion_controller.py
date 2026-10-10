from controllers.crud import crud_blueprint
from services.exportacion_service import exportacion_service
from views.exportacion_schema import ExportacionPageSchema, ExportacionQuerySchema, ExportacionSchema

blp = crud_blueprint(
    name="exportaciones",
    description="Registros de exportación del mercado (datos de entrenamiento)",
    service=exportacion_service,
    schema=ExportacionSchema,
    query_schema=ExportacionQuerySchema,
    page_schema=ExportacionPageSchema,
    label="exportaciones",
)
