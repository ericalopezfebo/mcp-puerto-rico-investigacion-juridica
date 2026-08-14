from __future__ import annotations

LEXJURIS_SEARCH_URL = "https://www.lexjuris.com/lexbusquedas.htm"


async def search(_query: str, limit: int = 20) -> list[dict]:
    """Placeholder adapter: discovery is explicit until the site's public search
    contract is verified. Never fabricates LexJuris results.
    """
    return []
