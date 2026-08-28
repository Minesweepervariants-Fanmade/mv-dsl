"""GQuad：无方（[1Q]）——每个 2x2 至少一个雷。

对照官方 BuildMetaConstraints case "[1Q]"（mv2 反编译 1681 行起）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Or, all_of
from .constraint import Constraint


class GQuad(Constraint):
    id = "Q"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height - 1):
            for c in range(puzzle.width - 1):
                four = [
                    mine_vars[(r, c)],
                    mine_vars[(r + 1, c)],
                    mine_vars[(r, c + 1)],
                    mine_vars[(r + 1, c + 1)],
                ]
                clauses.append(Or(tuple(BVar(vid) for vid in four)))
        return all_of(clauses)
