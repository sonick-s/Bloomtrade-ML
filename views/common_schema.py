from marshmallow import Schema, fields, validate


class TimestampSchema(Schema):
    """Campos comunes de BaseModel: solo de salida."""

    id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PaginationQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


def page_schema(item_schema, name):
    """Crea el schema de respuesta paginada para una entidad."""
    return Schema.from_dict(
        {
            "items": fields.List(fields.Nested(item_schema)),
            "total": fields.Integer(),
            "page": fields.Integer(),
            "per_page": fields.Integer(),
            "pages": fields.Integer(),
        },
        name=name,
    )


def to_page(pagination):
    return {
        "items": pagination.items,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
    }
