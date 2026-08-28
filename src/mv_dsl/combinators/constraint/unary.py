"""GUnary：一元（[1U]）——所有雷不能与其他雷相邻（4 邻全非雷）。

对照官方 BuildMetaConstraints case "[U]"（mv2 反编译 1291-1312 行）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Not, Or, all_of
from .constraint import Constraint


class CUnary(Constraint):
    id = "U"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                neighbors = []
                for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width:
                        neighbors.append(mine_vars[(nr, nc)])
                clauses.append(
                    Or((Not(BVar(mine_vars[(r, c)])),) + tuple(Not(BVar(v)) for v in neighbors))
                )
        return all_of(clauses)
