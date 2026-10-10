from flask import Blueprint, render_template

# Frontend: solo devuelve páginas HTML. Los datos se piden a la API (/api/v1) con fetch.
# Es un Blueprint normal de Flask (no flask-smorest), por eso no aparece en Swagger.
web_bp = Blueprint(
    "web",
    __name__,
    template_folder=".",  # raíz de web/: index.html es el layout; las páginas están en pages/
    static_folder="pages/js",
    static_url_path="/web/js",
)


@web_bp.route("/")
def dashboard():
    return render_template("pages/dashboard.html")


@web_bp.route("/modelos")
def modelos():
    return render_template("pages/model-uptodate.html")


@web_bp.route("/predicciones")
def predicciones():
    return render_template("pages/predicciones.html")
