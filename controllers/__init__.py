from controllers.dataset_controller import blp as dataset_blp
from controllers.exportacion_controller import blp as exportacion_blp
from controllers.health_controller import blp as health_blp
from controllers.inventario_finca_controller import blp as inventario_finca_blp
from controllers.modelo_controller import blp as modelo_blp
from controllers.pronostico_controller import blp as pronostico_blp

BLUEPRINTS = [health_blp, dataset_blp, exportacion_blp, inventario_finca_blp, modelo_blp, pronostico_blp]


def register_blueprints(api, prefix):
    # Antepone el prefijo global (/api/v1) a cada blueprint
    for blp in BLUEPRINTS:
        api.register_blueprint(blp, url_prefix=f"{prefix}{blp.url_prefix or ''}")
