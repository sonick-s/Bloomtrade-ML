from sqlalchemy.exc import IntegrityError

from config import db
from config.global_exceptions import BadRequestException, ConflictException, NotFoundException

# Códigos de error de MySQL/MariaDB que se traducen a respuestas claras
_DUPLICATE_ENTRY = 1062
_ROW_IS_REFERENCED = 1451
_NO_REFERENCED_ROW = 1452


class BaseService:
    """CRUD genérico. Cada servicio define su modelo y sobrescribe validate() con sus reglas."""

    model = None
    entity_name = "Registro"

    def list(self, page=1, per_page=20, **filters):
        query = db.select(self.model)
        for field, value in filters.items():
            query = query.where(getattr(self.model, field) == value)
        query = query.order_by(self.model.id.desc())
        return db.paginate(query, page=page, per_page=per_page, error_out=False)

    def get(self, entity_id):
        entity = db.session.get(self.model, entity_id)
        if entity is None:
            raise NotFoundException(f"{self.entity_name} {entity_id} no existe")
        return entity

    def create(self, data):
        self.validate(data)
        entity = self.model(**data)
        db.session.add(entity)
        self.commit()
        return entity

    def update(self, entity_id, data):
        entity = self.get(entity_id)
        self.validate(data, entity)
        for field, value in data.items():
            setattr(entity, field, value)
        self.commit()
        return entity

    def delete(self, entity_id):
        entity = self.get(entity_id)
        db.session.delete(entity)
        self.commit()

    def validate(self, data, current=None):
        """Reglas de negocio antes de guardar. current es la entidad actual en un update."""

    @staticmethod
    def merged(data, current, field):
        """Valor que tendrá el campo tras guardar: el nuevo si viene en data, si no el actual."""
        if field in data:
            return data[field]
        return getattr(current, field, None)

    @staticmethod
    def commit():
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            code = exc.orig.args[0] if exc.orig and exc.orig.args else None
            if code == _NO_REFERENCED_ROW:
                raise BadRequestException("El registro relacionado no existe") from exc
            if code == _ROW_IS_REFERENCED:
                raise ConflictException("No se puede eliminar: otros registros dependen de él") from exc
            if code == _DUPLICATE_ENTRY:
                raise ConflictException("Ya existe un registro con esos datos únicos") from exc
            raise ConflictException("Los datos no cumplen las restricciones de la base de datos") from exc
