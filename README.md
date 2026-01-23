# leopa-color

A FastAPI + htmx color demonstration application.

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for Python package management.

### Installation

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

## Development

### Running the Application

```bash
uv run uvicorn leopa_color.main:app --reload
```

Visit http://localhost:8000 in your browser.

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
├── src/
│   └── leopa_color/      # Application code
├── tests/                # Test files
├── templates/            # Jinja2 templates
├── static/               # Static files (CSS, JS, images)
├── .github/
│   └── workflows/        # GitHub Actions CI
├── pyproject.toml        # Project configuration
└── .pre-commit-config.yaml  # Pre-commit configuration
```
