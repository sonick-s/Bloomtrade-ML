from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import db


def check_database():
    try:
        db.session.execute(text("SELECT 1"))
        return "conectada"
    except SQLAlchemyError as exc:
        db.session.rollback()
        return f"error: {exc.__class__.__name__}"


def get_status():
    database = check_database()
    return {
        "status": "ok" if database == "conectada" else "degradado",
        "mensaje": "¡Hola, Mundo desde Flask!",
        "database": database,
    }
