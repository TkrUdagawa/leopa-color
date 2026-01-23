"""Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Leopa Color")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
