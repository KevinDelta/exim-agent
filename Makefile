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

