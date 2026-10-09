from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from config.database import db


class AppException(Exception):
    status_code = 500
    status = "Internal Server Error"

    def __init__(self, message=None):
        super().__init__(message)
        self.message = message or self.status


class BadRequestException(AppException):
    status_code = 400
    status = "Bad Request"


class UnauthorizedException(AppException):
    status_code = 401
    status = "Unauthorized"


class ForbiddenException(AppException):
    status_code = 403
    status = "Forbidden"


class NotFoundException(AppException):
    status_code = 404
    status = "Not Found"


class ConflictException(AppException):
    status_code = 409
    status = "Conflict"


def _response(status_code, status, message):
    return {"code": status_code, "status": status, "message": message}, status_code


def init_global_exceptions(app):
    # Los errores HTTP de Flask (abort(404), validaciones 422, etc.) ya los formatea flask-smorest.

    @app.errorhandler(AppException)
    def handle_app_exception(exc):
        return _response(exc.status_code, exc.status, exc.message)

    @app.errorhandler(SQLAlchemyError)
    def handle_db_exception(exc):
        db.session.rollback()
        app.logger.exception("Error de base de datos")
        return _response(500, "Internal Server Error", "Error de base de datos")

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc):
        if isinstance(exc, HTTPException):
            return exc
        app.logger.exception("Error no controlado")
        return _response(500, "Internal Server Error", "Error interno del servidor")
