from marshmallow import fields, validate

from views.common_schema import PaginationQuerySchema, TimestampSchema, page_schema

POSITIVO = validate.Range(min=0)


class PronosticoSchema(TimestampSchema):
    modelo_id = fields.Integer(required=True)
    tipo_flor = fields.String(required=True, validate=validate.Length(min=1, max=50))
    pais_destino = fields.String(required=True, validate=validate.Length(min=1, max=80))
    periodo = fields.Date(required=True)
    volumen_kg_pred = fields.Float(required=True, validate=POSITIVO)
    limite_inf = fields.Float(allow_none=True, validate=POSITIVO)
    limite_sup = fields.Float(allow_none=True, validate=POSITIVO)


class PronosticoQuerySchema(PaginationQuerySchema):
    modelo_id = fields.Integer()
    tipo_flor = fields.String()
    pais_destino = fields.String()


PronosticoPageSchema = page_schema(PronosticoSchema, "PronosticoPage")
