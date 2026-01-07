# Contributing to py-apple-foundation

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/prathwish/py-apple-foundation.git
   cd py-apple-foundation
   ```

2. Install in development mode with dev dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

Swift binaries are automatically compiled during installation.

## Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=apple_foundation
```

## Code Style

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

## Type Checking

```bash
mypy src/
```

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Requirements

- macOS 26+ (Tahoe)
- Python 3.10+
- Swift toolchain
