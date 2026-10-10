from controllers.crud import crud_blueprint
from services.inventario_finca_service import inventario_finca_service
from views.inventario_finca_schema import (
    InventarioFincaPageSchema,
    InventarioFincaQuerySchema,
    InventarioFincaSchema,
)

blp = crud_blueprint(
    name="inventario",
    description="Stock y cosechas de la finca (no se usan para entrenar)",
    service=inventario_finca_service,
    schema=InventarioFincaSchema,
    query_schema=InventarioFincaQuerySchema,
    page_schema=InventarioFincaPageSchema,
    label="lotes de inventario",
)
