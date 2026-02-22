# Entropic v0.7.0-dev — Project Commands
# Run `just` to see all available recipes

default:
    @just --list

# Run all tests
test:
    python3 -m pytest tests/ -v --tb=short

# Run tests matching a pattern
test-match pattern:
    python3 -m pytest tests/ -v --tb=short -k "{{pattern}}"

# Lint and auto-fix Python
lint:
    ruff check --fix . && ruff format .

# Lint check only (no fix)
lint-check:
    ruff check .

# Run full quality gate (lint + tests)
quality:
    ruff check . && python3 -m pytest tests/ -v --tb=short

# Start the web server
serve:
    python3 server.py

# Count lines of code
stats:
    find . -name '*.py' -not -path './__pycache__/*' -not -path './build/*' -not -path './dist/*' | xargs wc -l | tail -1
