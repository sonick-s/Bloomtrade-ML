from marshmallow import Schema, fields


class HealthSchema(Schema):
    status = fields.String()
    mensaje = fields.String()
    database = fields.String()
