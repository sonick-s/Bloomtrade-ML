from controllers.crud import crud_blueprint
from services.carga_service import cargar_csv
from services.dataset_service import dataset_service
from views.dataset_schema import (
    DatasetArchivoSchema,
    DatasetCargaSchema,
    DatasetPageSchema,
    DatasetQuerySchema,
    DatasetSchema,
)

blp = crud_blueprint(
    name="datasets",
    description="Versiones de los CSV cargados (mercado o interno)",
    service=dataset_service,
    schema=DatasetSchema,
    query_schema=DatasetQuerySchema,
    page_schema=DatasetPageSchema,
    label="datasets",
)


# flask-smorest no documenta bien archivo + formulario en la misma petición: se describe a mano
DOC_UPLOAD = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["archivo", "nombre", "tipo"],
                    "properties": {
                        "archivo": {"type": "string", "format": "binary"},
                        "nombre": {"type": "string"},
                        "tipo": {"type": "string", "enum": ["mercado", "interno"]},
                        "origen": {"type": "string", "enum": ["base", "usuario"], "default": "usuario"},
                    },
                }
            }
        },
    }
}


@blp.route("/upload", methods=["POST"])
@blp.doc(**DOC_UPLOAD)
@blp.arguments(DatasetArchivoSchema, location="files")
@blp.arguments(DatasetCargaSchema, location="form")
@blp.response(201, DatasetSchema)
def upload(archivos, datos):
    """Carga un CSV: lo valida, crea el dataset e inserta sus filas (mercado o inventario)"""
    return cargar_csv(archivos["archivo"], **datos)
