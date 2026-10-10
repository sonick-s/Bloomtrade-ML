from controllers.crud import crud_blueprint
from services.dataset_service import dataset_service
from views.dataset_schema import DatasetPageSchema, DatasetQuerySchema, DatasetSchema

blp = crud_blueprint(
    name="datasets",
    description="Versiones de los CSV cargados (mercado o interno)",
    service=dataset_service,
    schema=DatasetSchema,
    query_schema=DatasetQuerySchema,
    page_schema=DatasetPageSchema,
    label="datasets",
)
