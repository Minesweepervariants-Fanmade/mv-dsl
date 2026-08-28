"""GH2：横向（[2H]）——所有雷必须存在横向相邻的雷。

对照官方 BuildMetaConstraints case "[2H]"（mv2 反编译 1723-1743 行）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Not, Or, all_of
from .constraint import Constraint


class GH2(Constraint):
    id = "2H"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                neighbors = []
                if c > 0:
                    neighbors.append(mine_vars[(r, c - 1)])
                if c < puzzle.width - 1:
                    neighbors.append(mine_vars[(r, c + 1)])
                clauses.append(
                    Or((Not(BVar(mine_vars[(r, c)])),) + tuple(BVar(v) for v in neighbors))
                )
        return all_of(clauses)
