from contextlib import asynccontextmanager
from fastapi import FastAPI

from your_pipeline.db.repo import Database
from your_pipeline.services.routers.repriced import router as repriced_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = Database()
    try:
        yield
    finally:
        app.state.db.dispose()

app = FastAPI(title="Repriced Products API", lifespan=lifespan)
app.include_router(repriced_router)
