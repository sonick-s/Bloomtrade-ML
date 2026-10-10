from marshmallow import Schema, fields


class PrediccionQuerySchema(Schema):
    dataset_id = fields.Integer(required=True, metadata={"description": "Dataset interno (inventario de la finca)"})
