# leopa-color

Infrared image colorization web app for leopard gecko pet cameras. Uses AI (Replicate API with IP-Adapter SDXL) to colorize infrared/night vision images using reference color photos.

## Features

- Upload reference color images of your leopard gecko
- Upload infrared images from pet cameras
- AI-powered colorization using style transfer
- Drag-and-drop UI with real-time progress updates
- Download colorized results

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for Python package management.

### Installation

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Get a Replicate API token from https://replicate.com and add it to `.env`:
   ```
   REPLICATE_API_TOKEN=r8_xxxxx
   ```

## Usage

### Running the Application

```bash
uv run uvicorn leopa_color.main:app --reload
```

Visit http://localhost:8000/colorize in your browser.

### How to Colorize Images

1. **Upload Reference Images**: Add color photos of your leopard gecko. These teach the AI what colors to use.

2. **Select References**: Click on reference images to select them (blue border = selected).

3. **Upload Infrared Image**: Drag and drop an infrared image from your pet camera.

4. **Colorize**: Click the Colorize button and wait for processing.

5. **Download**: Once complete, download your colorized image.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/colorize` | Main colorization UI |
| POST | `/api/colorize` | Start colorization job |
| GET | `/api/colorize/{job_id}` | Check job status |
| GET | `/api/colorize/{job_id}/result` | Download result image |
| GET | `/api/references` | List reference images |
| POST | `/api/references` | Upload reference image |
| GET | `/api/references/{id}` | Get reference image |
| DELETE | `/api/references/{id}` | Delete reference image |

## Development

### Testing

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov
```

### Linting and Type Checking

```bash
# Run ruff linter
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking with pyright
uv run pyright
```

### Pre-commit

Pre-commit hooks will automatically run on git commit. To run manually:

```bash
uv run pre-commit run --all-files
```

## Project Structure

```
leopa-color/
├── src/leopa_color/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── models.py            # Pydantic models
│   ├── routers/
│   │   ├── colorize.py      # Colorization endpoints
│   │   └── references.py    # Reference image endpoints
│   └── services/
│       ├── replicate_service.py  # Replicate API integration
│       └── storage_service.py    # Image storage management
├── templates/               # Jinja2 templates
├── static/
│   ├── css/styles.css      # Application styles
│   └── js/upload.js        # Upload and UI logic
├── tests/                  # Test files
├── data/                   # Image storage (gitignored)
│   ├── references/         # Reference color images
│   ├── uploads/            # Uploaded infrared images
│   └── results/            # Colorized results
├── .github/workflows/      # GitHub Actions CI
├── pyproject.toml          # Project configuration
└── .pre-commit-config.yaml # Pre-commit configuration
```

## Technology Stack

- **Backend**: FastAPI, Python 3.12+
- **Frontend**: htmx, vanilla JavaScript
- **Templates**: Jinja2
- **AI**: Replicate API (IP-Adapter SDXL)
- **Package Manager**: uv
