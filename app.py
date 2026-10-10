from flask import Flask

from config import Config, init_cors, init_db, init_global_exceptions, init_swagger
from controllers import register_blueprints
import models  # noqa: F401  registra los modelos en SQLAlchemy
from web import web_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    init_cors(app)
    init_db(app)
    api = init_swagger(app)
    init_global_exceptions(app)
    register_blueprints(api, app.config["API_PREFIX"])
    app.register_blueprint(web_bp)  # frontend (HTML), separado de la API

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
