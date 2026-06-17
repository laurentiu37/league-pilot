from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class LogEntry:
    ts: datetime
    event_type: str
    message: str
    game_id: Optional[str] = None


class EventLog:
    def __init__(self) -> None:
        self.entries: List[LogEntry] = []

    def add(self, event_type: str, message: str, *, game_id: Optional[str] = None) -> None:
        self.entries.append(LogEntry(datetime.now(), event_type, message, game_id))

    def dump(self) -> str:
        out = []
        for e in self.entries:
            s = f"[{e.ts.strftime('%Y-%m-%d %H:%M:%S')}] {e.event_type}: {e.message}"
            if e.game_id:
                s += f" (game_id={e.game_id})"
            out.append(s)
        return "\n".join(out)

    def dump_to_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.dump())
