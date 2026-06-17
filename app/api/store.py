from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

from app.use_cases.simulate_season import SimulateSeasonResult


@dataclass
class RunRecord:
    run_id: int
    result: SimulateSeasonResult


class InMemoryRunStore:
    def __init__(self) -> None:
        self._runs: Dict[int, RunRecord] = {}
        self._next_id: int = 1

    def save(self, result: SimulateSeasonResult) -> int:
        run_id = self._next_id
        self._next_id += 1
        self._runs[run_id] = RunRecord(run_id=run_id, result=result)
        return run_id

    def get(self, run_id: int) -> RunRecord:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return self._runs[run_id]
