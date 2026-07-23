# Fast Learning Guide: Git Hooks, pyproject.toml, and Python Tooling

## 1. What Are Git Hooks & How Pre-Commit/Pre-Push Work

### High-Level Concept
Git hooks are custom shell scripts that Git automatically runs before or after specific actions like `commit` or `push`.

Instead of writing shell scripts by hand in `.git/hooks/`, we use **`pre-commit`** (a Python-based manager) configured via `.pre-commit-config.yaml`.

### Two-Stage Hook Lifecycle
1. **`pre-commit` Stage (<1s runtime)**: Runs locally *before* creating a commit.
   - **Ruff**: Linter & auto-formatter replacing Flake8, Black, and isort.
   - **Basic Cleanup**: Fixes trailing whitespace, end-of-file formatting, and checks YAML/JSON syntax.
2. **`pre-push` Stage (Full Security Analysis)**: Runs locally *before* pushing to remote repositories.
   - **Mypy**: Static type checking to catch type mismatches.
   - **Bandit**: Security analysis scanning ASTs for vulnerabilities (e.g., hardcoded tokens or unsafe calls).

### Official Recommended Resources
- [Pre-commit Documentation](https://pre-commit.com/)
- [Ruff Official Docs](https://docs.astral.sh/ruff/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [PyCQA Bandit Docs](https://bandit.readthedocs.io/)

---

## 2. Understanding `pyproject.toml` (PEP 518 / PEP 621 Standard)

### Why `pyproject.toml` Replaces Legacy Files
Historically, Python projects required multiple fragmented configuration files:
- `requirements.txt` for production dependencies
- `requirements-dev.txt` for development dependencies
- `setup.py` / `setup.cfg` for packaging
- `.flake8`, `pytest.ini`, `mypy.ini` for tool settings

Modern Python uses **`pyproject.toml`** as the single source of truth for:
1. **Project Metadata** (`[project]`): Package name, version, Python requirements.
2. **Dependencies** (`[project.dependencies]` & `[project.optional-dependencies]`): Production & dev packages.
3. **Tool Configurations** (`[tool.ruff]`, `[tool.mypy]`, `[tool.bandit]`, `[tool.pytest.ini_options]`): Replaces standalone tool config files.

---

## 3. Core Tooling Matrix & What to Study

| Tool | Purpose | Key Concept to Learn | Recommended Fast Tutorial |
|---|---|---|---|
| **Ruff** | Code Linting & Formatting | Rule codes: `E` (Syntax), `F` (Flake8), `I` (Import sorting), `N` (Naming conventions). | Run `ruff check .` and `ruff format .` |
| **Mypy** | Static Type Checker | Type annotations (`def func(x: int) -> str:`), type guards, handling optional values. | Run `mypy app` |
| **Bandit** | Security Scanner | AST security checks (`B105` hardcoded passwords, `B608` SQL injection). | Run `bandit -r app` |
| **Pydantic Settings** | Environment Config | `BaseSettings` reading environment variables with zero code secrets. | FastAPI Settings documentation |

---

## 4. Quick Self-Study Checklist (15 Minutes)

1. Read the [FastAPI Official First Steps Guide](https://fastapi.tiangolo.com/tutorial/first-steps/) to understand Uvicorn & Uvicorn Lifespan.
2. Skim [PEP 621 – Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/).
3. Run `pre-commit run --all-files` in your terminal to see how hooks analyze every file.
