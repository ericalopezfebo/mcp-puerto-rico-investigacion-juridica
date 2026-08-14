from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Decision:
    title: str = ""
    url: str = ""
    source: str = ""
    citation: str = ""
    case_number: str = ""
    date: str = ""
    judge: str = ""
    subject: str = ""
    snippet: str = ""
    page: int | None = None
    verified: bool = False
    verification_status: str = "unverified"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
