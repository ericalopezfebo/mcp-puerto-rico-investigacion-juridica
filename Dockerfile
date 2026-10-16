FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY server.py research_server.py smart_server.py legal_research_loop.py search_tuning.py doctrine_ontology.py corpus_index.py corpus_runtime.py authority_reader.py jrt_server.py vigencia_server.py legislative_graph.py mixed_server.py remote_server.py bootstrap_server.py bootstrap_remote.py ./
COPY data ./data

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "bootstrap_remote.py"]
