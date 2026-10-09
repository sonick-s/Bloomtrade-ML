from controllers.health_controller import blp as health_blp


def register_blueprints(api):
    api.register_blueprint(health_blp)
