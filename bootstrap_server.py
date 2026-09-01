"""Production stdio bootstrap that enables the persistent corpus runtime."""
from __future__ import annotations

import mixed_server
import legal_research_loop  # noqa: F401 - registers bounded agentic research tool
import corpus_runtime  # noqa: F401 - applies corpus-first runtime patches and tools
import authority_directory  # noqa: F401 - discovery-only jurisprudence directory context
import authority_directory_extended  # noqa: F401 - property/family/real-rights/succession discovery context

VERSION = "0.16.0"
mixed_server.VERSION = VERSION
mixed_server.research_server.VERSION = VERSION
mcp = mixed_server.mcp


def main() -> None:
    mixed_server.main()


if __name__ == "__main__":
    main()
