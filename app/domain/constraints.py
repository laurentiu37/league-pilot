from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import List, Tuple

DateWindow = Tuple[date, date]


@dataclass
class Constraints:
    hard_block_windows: List[DateWindow] = field(default_factory=list)

    def is_hard_blocked(self, d: date) -> bool:
        for a, b in self.hard_block_windows:
            if a <= d <= b:
                return True
        return False
