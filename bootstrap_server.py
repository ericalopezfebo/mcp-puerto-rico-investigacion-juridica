"""Production stdio bootstrap that enables the persistent corpus runtime."""
from __future__ import annotations

import mixed_server
import corpus_runtime  # noqa: F401 - applies corpus-first runtime patches and tools
import authority_directory  # noqa: F401 - discovery-only jurisprudence directory context

VERSION = "0.15.1"
mixed_server.VERSION = VERSION
mixed_server.research_server.VERSION = VERSION
mcp = mixed_server.mcp


def main() -> None:
    mixed_server.main()


if __name__ == "__main__":
    main()
