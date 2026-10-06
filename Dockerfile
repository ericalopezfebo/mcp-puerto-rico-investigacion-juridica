FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 10001 mcp && \
    useradd --system --uid 10001 --gid mcp --home-dir /nonexistent --shell /usr/sbin/nologin mcp

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY server.py research_server.py smart_server.py search_tuning.py doctrine_ontology.py corpus_index.py corpus_runtime.py authority_reader.py jrt_server.py vigencia_server.py legislative_graph.py mixed_server.py remote_server.py bootstrap_server.py bootstrap_remote.py ./
COPY data ./data

RUN pip install --no-cache-dir . && chown -R mcp:mcp /app

USER 10001:10001

EXPOSE 8000

CMD ["python", "bootstrap_remote.py"]
