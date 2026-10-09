from flask.views import MethodView
from flask_smorest import Blueprint

from services import health_service
from views.health_schema import HealthSchema

blp = Blueprint("health", __name__, url_prefix="/api/health", description="Verificación del servidor y la base de datos")


@blp.route("/")
class HealthController(MethodView):
    @blp.response(200, HealthSchema)
    def get(self):
        """Comprueba que la API está arriba y que MySQL responde"""
        return health_service.get_status()
