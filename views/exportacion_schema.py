from marshmallow import fields, validate

from views.common_schema import PaginationQuerySchema, TimestampSchema, page_schema

POSITIVO = validate.Range(min=0)


class ExportacionSchema(TimestampSchema):
    dataset_id = fields.Integer(required=True)
    fecha_despacho = fields.Date(required=True)
    anio = fields.Integer(dump_only=True)
    mes = fields.Integer(dump_only=True)
    temporada = fields.String(allow_none=True, validate=validate.Length(max=30))
    exportador = fields.String(allow_none=True, validate=validate.Length(max=100))
    tamano_empresa = fields.String(allow_none=True, validate=validate.Length(max=20))
    provincia_origen = fields.String(allow_none=True, validate=validate.Length(max=50))
    aeropuerto_salida = fields.String(allow_none=True, validate=validate.Length(max=80))
    subpartida_nandina = fields.String(allow_none=True, validate=validate.Length(max=12))
    tipo_flor = fields.String(required=True, validate=validate.Length(min=1, max=50))
    pais_destino = fields.String(required=True, validate=validate.Length(min=1, max=80))
    tiempo_transito_dias = fields.Integer(allow_none=True, validate=validate.Range(min=0, max=255))
    volumen_kg = fields.Float(required=True, validate=POSITIVO)
    precio_fob_usd_kg = fields.Float(allow_none=True, validate=POSITIVO)
    valor_fob_usd = fields.Float(required=True, validate=POSITIVO)


class ExportacionQuerySchema(PaginationQuerySchema):
    dataset_id = fields.Integer()
    tipo_flor = fields.String()
    pais_destino = fields.String()
    anio = fields.Integer()
    mes = fields.Integer(validate=validate.Range(min=1, max=12))


ExportacionPageSchema = page_schema(ExportacionSchema, "ExportacionPage")
