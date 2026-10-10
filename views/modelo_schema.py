from marshmallow import fields, validate

from views.common_schema import PaginationQuerySchema, TimestampSchema, page_schema


class ModeloSchema(TimestampSchema):
    version = fields.Integer(required=True, validate=validate.Range(min=1))
    algoritmo = fields.String(required=True, validate=validate.Length(min=1, max=50))
    ruta_artefacto = fields.String(required=True, validate=validate.Length(min=1, max=255))
    parametros = fields.Dict(allow_none=True)
    metricas = fields.Dict(allow_none=True)
    # Solo se cambia con POST /modelos/<id>/activar
    activo = fields.Boolean(dump_only=True)
    dataset_ids = fields.List(fields.Integer(), load_default=list)


class ModeloQuerySchema(PaginationQuerySchema):
    algoritmo = fields.String()
    activo = fields.Boolean()


ModeloPageSchema = page_schema(ModeloSchema, "ModeloPage")
