"""GFlowers：花田（[2F]）——染色格中的雷周围四格恰有 1 个雷。

对照官方 BuildMetaConstraints case "[2F]"（mv2 反编译 1313-1346 行）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Cmp, Lin, Not, Or, all_of, sum_of
from .constraint import Constraint


class GFlowers(Constraint):
    id = "2F"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                if not puzzle.cells[r][c].colored:
                    continue
                neighbors = []
                for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width:
                        neighbors.append(mine_vars[(nr, nc)])
                total = sum_of(Lin(((v, 1),)) for v in neighbors)
                clauses.append(
                    Or((Not(BVar(mine_vars[(r, c)])), Cmp("==", total, Lin((), 1))))
                )
        return all_of(clauses)
