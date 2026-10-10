from marshmallow import fields, validate

from models import InventarioFinca
from views.common_schema import PaginationQuerySchema, TimestampSchema, page_schema

POSITIVO = validate.Range(min=0)


class InventarioFincaSchema(TimestampSchema):
    dataset_id = fields.Integer(required=True)
    codigo_lote = fields.String(allow_none=True, validate=validate.Length(max=50))
    bloque = fields.String(allow_none=True, validate=validate.Length(max=50))
    tipo_flor = fields.String(required=True, validate=validate.Length(min=1, max=50))
    variedad = fields.String(allow_none=True, validate=validate.Length(max=80))
    color = fields.String(allow_none=True, validate=validate.Length(max=40))
    grado_calidad = fields.String(allow_none=True, validate=validate.Length(max=30))
    longitud_tallo_cm = fields.Integer(allow_none=True, validate=POSITIVO)
    stock_tallos = fields.Integer(allow_none=True, validate=POSITIVO)
    stock_kg = fields.Float(required=True, validate=POSITIVO)
    estado = fields.String(load_default="en_cultivo", validate=validate.OneOf(InventarioFinca.ESTADOS))
    fecha_cosecha = fields.Date(required=True)
    fecha_salida_desde = fields.Date(required=True)
    fecha_salida_hasta = fields.Date(required=True)
    vida_util_dias = fields.Integer(allow_none=True, validate=validate.Range(min=0, max=255))
    costo_produccion_usd_kg = fields.Float(allow_none=True, validate=POSITIVO)
    precio_minimo_usd_kg = fields.Float(allow_none=True, validate=POSITIVO)
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=500))


class InventarioFincaQuerySchema(PaginationQuerySchema):
    dataset_id = fields.Integer()
    tipo_flor = fields.String()
    estado = fields.String(validate=validate.OneOf(InventarioFinca.ESTADOS))


InventarioFincaPageSchema = page_schema(InventarioFincaSchema, "InventarioFincaPage")
