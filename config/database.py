import os

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import URL

load_dotenv()

db = SQLAlchemy()


def _database_uri():
    # URL.create escapa caracteres especiales (@, :, /, #...) de usuario y contraseña
    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
        query={"charset": "utf8mb4"},
    )


def init_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}
    db.init_app(app)
