"""Production HTTP bootstrap that enables the persistent corpus runtime."""
from __future__ import annotations

import bootstrap_server  # noqa: F401 - loads corpus-first patches before HTTP setup
import remote_server


def main() -> None:
    remote_server.main()


if __name__ == "__main__":
    main()
