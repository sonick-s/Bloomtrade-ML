from flask_smorest import Blueprint

from services import dashboard_service

blp = Blueprint("dashboard", __name__, url_prefix="/dashboard", description="Resumen global para el dashboard")


@blp.route("/resumen")
@blp.response(200)
def resumen():
    """Estado de los datos, modelo activo, histórico mensual y pronóstico agregado"""
    return dashboard_service.resumen()
