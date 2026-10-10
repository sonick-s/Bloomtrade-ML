from flask_smorest import Blueprint

from services.prediccion_service import recomendar
from views.prediccion_schema import PrediccionQuerySchema

blp = Blueprint("predicciones", __name__, url_prefix="/predicciones",
                description="Recomendaciones de mercado para el inventario de la finca")


@blp.route("/inventario")
@blp.arguments(PrediccionQuerySchema, location="query")
@blp.response(200)
def inventario(args):
    """Cruza cada lote del inventario con el pronóstico del modelo activo y reparte su stock por mercado"""
    return recomendar(args["dataset_id"])
