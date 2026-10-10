from flask.views import MethodView
from flask_smorest import Blueprint

from views.common_schema import to_page


def crud_blueprint(name, description, service, schema, query_schema, page_schema, label):
    """
    Crea un Blueprint con el CRUD estándar de una entidad:
        GET    /<name>/        lista paginada con filtros
        POST   /<name>/        crea
        GET    /<name>/<id>    obtiene uno
        PATCH  /<name>/<id>    actualiza parcialmente
        DELETE /<name>/<id>    elimina
    """
    blp = Blueprint(name, __name__, url_prefix=f"/{name}", description=description)
    # Subclase con nombre propio para que Swagger no la confunda con el schema completo
    update_schema = type(f"{schema.__name__.removesuffix('Schema')}UpdateSchema", (schema,), {})

    class Collection(MethodView):
        @blp.arguments(query_schema, location="query")
        @blp.response(200, page_schema)
        def get(self, args):
            return to_page(service.list(**args))

        @blp.arguments(schema)
        @blp.response(201, schema)
        def post(self, data):
            return service.create(data)

    class Item(MethodView):
        @blp.response(200, schema)
        def get(self, entity_id):
            return service.get(entity_id)

        @blp.arguments(update_schema(partial=True))
        @blp.response(200, schema)
        def patch(self, data, entity_id):
            return service.update(entity_id, data)

        @blp.response(204)
        def delete(self, entity_id):
            service.delete(entity_id)

    # Descripciones que se muestran en Swagger
    Collection.get.__doc__ = f"Lista {label} (paginado y con filtros)"
    Collection.post.__doc__ = f"Crea {label}"
    Item.get.__doc__ = f"Obtiene {label} por id"
    Item.patch.__doc__ = f"Actualiza {label} (solo los campos enviados)"
    Item.delete.__doc__ = f"Elimina {label}"

    blp.route("/")(Collection)
    blp.route("/<int:entity_id>")(Item)
    return blp
