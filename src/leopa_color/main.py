"""Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from leopa_color.config import get_settings
from leopa_color.routers import colorize, references


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    settings = get_settings()
    settings.ensure_directories()
    yield


app = FastAPI(title="Leopa Color", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount data directory for serving uploaded and result images
settings = get_settings()
data_dir = Path(settings.data_dir)
if not data_dir.exists():
    data_dir.mkdir(parents=True)
app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")

# Include routers
app.include_router(references.router)
app.include_router(colorize.router)

# Configure templates
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the index page."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/color/{color_name}")
async def get_color(color_name: str) -> dict[str, str]:
    """Get color information."""
    colors = {
        "red": "#FF0000",
        "green": "#00FF00",
        "blue": "#0000FF",
        "yellow": "#FFFF00",
        "purple": "#800080",
    }
    return {
        "name": color_name,
        "hex": colors.get(color_name.lower(), "#000000"),
    }
