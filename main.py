from fastapi import FastAPI

from config import settings
from src.routes.AuthRouter import router as user_router
from src.routes.PerformanceRouter import router as ps_router

app = FastAPI(
    title="RetireSaveUp",
    version=settings.VERSION
)


app.include_router(user_router)
app.include_router(ps_router)