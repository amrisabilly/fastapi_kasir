from .kategori import router as kategori_router
from .menu import router as menu_router
from .ingredients import router as ingredients_router
from .stock_opname import router as stock_opname_router
from .customers import router as customers_router

__all__ = [
    "kategori_router",
    "menu_router",
    "ingredients_router",
    "stock_opname_router"
    "customers_router"
]