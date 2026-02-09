from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.infrastructure.firebase import init_firebase
from app.pages import render_root_page


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_firebase()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Landing page with links to API documentation."""
    return HTMLResponse(content=render_root_page(settings.app_name))
