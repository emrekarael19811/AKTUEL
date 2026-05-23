from fastapi import APIRouter
from app.api.v1 import markets, catalogs, products, search, watchlist

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(markets.router)
api_router.include_router(catalogs.router)
api_router.include_router(products.router)
api_router.include_router(search.router)
api_router.include_router(watchlist.router)
