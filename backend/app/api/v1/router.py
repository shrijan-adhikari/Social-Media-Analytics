"""Central API v1 router bundling all analytical endpoints."""

from fastapi import APIRouter

from app.api.v1.network import router as network_router
from app.api.v1.overview import router as overview_router
from app.api.v1.sentiment import router as sentiment_router
from app.api.v1.status import router as status_router
from app.api.v1.trends import router as trends_router
from app.api.v1.tweets import router as tweets_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(overview_router)
api_v1_router.include_router(tweets_router)
api_v1_router.include_router(sentiment_router)
api_v1_router.include_router(trends_router)
api_v1_router.include_router(network_router)
api_v1_router.include_router(status_router)
