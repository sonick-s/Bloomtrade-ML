from controllers.health_controller import blp as health_blp

BLUEPRINTS = [health_blp]


def register_blueprints(api, prefix):
    # Antepone el prefijo global (/api/v1) a cada blueprint
    for blp in BLUEPRINTS:
        api.register_blueprint(blp, url_prefix=f"{prefix}{blp.url_prefix or ''}")
