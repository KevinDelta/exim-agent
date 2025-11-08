# Repository Guidelines

## Project Structure & Module Organization

Backend lives in `src/exim_agent` with `application/` service flows, `domain/` models and tools, `infrastructure/` API/database/LLM adapters, and `config.py`. Pytest suites mirror this layout in `tests/`. Client code sits in `frontend/src` (App Router pages, components, hooks, lib), with shared assets in `static/`, `templates/`, and `public/`. Persistent embeddings belong in `data/`.

## Environment & Configuration

Sync backend dependencies with `uv sync` (CLI entry point `exim_agent.cli`). Copy `.env.example` to `.env` and `frontend/.env.example` to `.env.local`; keep secrets local only. Docker Compose volumes write to `data/chroma_db`, so clear personal files before committing.

## Build, Test, and Development Commands

`uv run fastapi dev src/exim_agent/infrastructure/api/main.py` launches the API with reload. `make build-project`, `make start-project`, and `make stop-project` wrap Docker Compose for the full stack. Run `uv run pytest` for backend tests and `uv run ruff check` (optionally `ruff format`) to enforce linting. For the frontend: `cd frontend && npm install`, `npm run dev` for local work, `npm run build` before release, and `npm run lint` / `npm run type-check` as PR gates.

## Coding Style & Naming Conventions

Python follows Ruff’s 120-character limit, snake_case functions, PascalCase classes, and Pydantic models for settings and payloads. Latest python syntax and practices. Organize new services under `application/` and pass dependencies explicitly. Next.js components use PascalCase filenames, colocated CSS-in-JS, and hook names prefixed with `use`.

## Testing Guidelines

Backend tests belong in `tests/test_<area>.py` and should exercise compliance workflows, LangChain tools, and API contracts. Mock remote LLM calls and fixture external data under `tests/fixtures/`. Maintain or improve coverage, and document intentional gaps in the PR. The frontend currently lacks automated tests—until they exist, record manual QA steps for UI work.

## Commit & Pull Request Guidelines

Use semantic commits (`feat`, `fix`, `refactor`, `chore`, etc.) with optional scope, e.g. `feat(compliance): add denial list retriever`; keep the subject imperative and ≤72 chars. PRs must summarize the change, list validation commands, link issues, and include screenshots or payload samples for UI/API shifts. Always rebase before requesting review and update docs or configuration samples when behavior changes.

## Security & Configuration Tips

Do not commit `.env*` files or raw customer data. Rotate API keys regularly, scrub sensitive values from logs, and prefer test doubles over live credentials. Large derived files belong in `data/` but should remain untracked unless explicitly required.
