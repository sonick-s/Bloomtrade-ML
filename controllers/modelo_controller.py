from controllers.crud import crud_blueprint
from services.entrenamiento_service import entrenar_modelo
from services.modelo_service import modelo_service
from views.modelo_schema import EntrenamientoSchema, EntrenarSchema, ModeloPageSchema, ModeloQuerySchema, ModeloSchema

blp = crud_blueprint(
    name="modelos",
    description="Versiones entrenadas del modelo (registro de modelos)",
    service=modelo_service,
    schema=ModeloSchema,
    query_schema=ModeloQuerySchema,
    page_schema=ModeloPageSchema,
    label="modelos",
)


@blp.route("/activo")
@blp.response(200, ModeloSchema)
def get_active():
    """Obtiene el modelo activo (el que usan las predicciones)"""
    return modelo_service.get_active()


@blp.route("/<int:entity_id>/activar", methods=["POST"])
@blp.response(200, ModeloSchema)
def activate(entity_id):
    """Activa este modelo y desactiva el anterior"""
    return modelo_service.activate(entity_id)


@blp.route("/entrenar", methods=["POST"])
@blp.arguments(EntrenarSchema)
@blp.response(201, EntrenamientoSchema)
def train(datos):
    """Entrena una versión nueva con los datasets de mercado, guarda sus pronósticos y la activa si mejora"""
    return entrenar_modelo(**datos)
