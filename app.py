from flask import Flask
from flask_cors import CORS
from flask_smorest import Api, Blueprint

# 1. Crear la aplicación Flask
app = Flask(__name__)

# 2. Habilitar CORS
CORS(app)

# 3. Configuración mínima para Swagger UI (OpenAPI)
app.config["API_TITLE"] = "Hola Mundo API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

api = Api(app)

# 4. Definir la ruta principal
blp = Blueprint("inicio", "inicio", url_prefix="/", description="Rutas de prueba")

@blp.route("/")
def hola_mundo():
    return {"mensaje": "¡Hola, Mundo desde Flask!"}

api.register_blueprint(blp)

# 5. Ejecutar el servidor
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)