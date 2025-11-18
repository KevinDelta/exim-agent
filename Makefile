build-project:
	docker compose build

start-project:
	docker compose up --build -d

stop-project:
	docker compose stop

check-collections:
	@docker exec agent-api /app/.venv/bin/python -c "\
import chromadb; \
client = chromadb.PersistentClient(path='/app/data/chroma_db'); \
collections = client.list_collections(); \
print('ChromaDB Collections:'); \
[print(f'  - {col.name}: {col.count()} documents') for col in collections]"

langgraph-dev:
	@if [ ! -d ".venv" ]; then \
		echo "Missing .venv. Run 'uv sync' (or equivalent) first."; \
		exit 1; \
	fi
	@if [ ! -x ".venv/bin/langgraph" ]; then \
		echo "LangGraph CLI not found in .venv. Re-run 'uv sync' to install dependencies."; \
		exit 1; \
	fi
	@. .venv/bin/activate && langgraph dev
