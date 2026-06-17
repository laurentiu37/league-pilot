from __future__ import annotations
from dataclasses import dataclass, field
import uuid


@dataclass(frozen=True)
class Team:
    name: str
    city: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
