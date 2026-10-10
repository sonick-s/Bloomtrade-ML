from marshmallow import Schema, fields, validate

from models import Dataset
from views.common_schema import PaginationQuerySchema, TimestampSchema, page_schema


class DatasetSchema(TimestampSchema):
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=150))
    archivo_original = fields.String(required=True, validate=validate.Length(min=1, max=255))
    tipo = fields.String(load_default="mercado", validate=validate.OneOf(Dataset.TIPOS))
    origen = fields.String(load_default="usuario", validate=validate.OneOf(Dataset.ORIGENES))
    filas = fields.Integer(load_default=0, validate=validate.Range(min=0))
    fecha_min = fields.Date(allow_none=True)
    fecha_max = fields.Date(allow_none=True)
    hash_sha256 = fields.String(required=True, validate=validate.Regexp(r"^[0-9a-f]{64}$"))
    estado = fields.String(load_default="pendiente", validate=validate.OneOf(Dataset.ESTADOS))
    errores = fields.Raw(allow_none=True)


class DatasetQuerySchema(PaginationQuerySchema):
    tipo = fields.String(validate=validate.OneOf(Dataset.TIPOS))
    origen = fields.String(validate=validate.OneOf(Dataset.ORIGENES))
    estado = fields.String(validate=validate.OneOf(Dataset.ESTADOS))


DatasetPageSchema = page_schema(DatasetSchema, "DatasetPage")
