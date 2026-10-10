from pathlib import Path

from flask import Blueprint, render_template, send_from_directory

CARPETA_ASSETS = Path(__file__).resolve().parent / "assets"

# Frontend: solo devuelve páginas HTML. Los datos se piden a la API (/api/v1) con fetch.
# Es un Blueprint normal de Flask (no flask-smorest), por eso no aparece en Swagger.
web_bp = Blueprint(
    "web",
    __name__,
    template_folder=".",  # raíz de web/: index.html es el layout; las páginas están en pages/
    static_folder="pages/js",
    static_url_path="/web/js",
)


@web_bp.route("/web/assets/<path:archivo>")
def assets(archivo):
    """Imágenes y otros archivos de web/assets/."""
    return send_from_directory(CARPETA_ASSETS, archivo)


@web_bp.route("/")
def dashboard():
    return render_template("pages/dashboard.html")


@web_bp.route("/modelos")
def modelos():
    return render_template("pages/model-uptodate.html")


@web_bp.route("/predicciones")
def predicciones():
    return render_template("pages/predicciones.html")


# Datos de la pantalla "Acerca de". Edita aquí los datos de los creadores.
# linkedin: URL completa (con tildes codificadas); se usa para el botón y el código QR.
# foto: nombre del archivo en web/assets/ (o una URL completa); sin foto se muestran las iniciales.
# foto_posicion: qué parte de la foto se ve en el círculo ("top", "center", "bottom"...).
# color: color de su mitad de la pantalla ("azul" o "verde", definidos en pages/about.html).
CREADORES = [
    {
        "nombre": "Omar Alexander Sani Satan",
        "rol": "Co-creador",
        "telefono": "0983407989",
        "correo": "omarxdj4@gmail.com",
        "linkedin": "https://www.linkedin.com/in/omar-sani-b9733a2b9/",
        "foto": "omarsani.png",
        "foto_posicion": "top",
        "color": "azul",
    },
    {
        "nombre": "Víctor Javier Cárdenas Trujillo",
        "rol": "Co-creador",
        "telefono": "0980508637",
        "correo": "victorjcardenast@gmail.com",
        "linkedin": "https://www.linkedin.com/in/v%C3%ADctor-javier-c%C3%A1rdenas-trujillo-73593983",
        "foto": "victor image.jpg",
        "color": "verde",
    },
]


@web_bp.route("/about")
def about():
    return render_template("pages/about.html", creadores=CREADORES)
