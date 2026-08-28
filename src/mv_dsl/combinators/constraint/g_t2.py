"""GT2：无三连（[2T]）——雷与非雷在横竖方向都不能构成三连。

即每个 3 连窗口恰有 1 或 2 个雷（1≤Σ≤2）。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Lin, all_of, sum_of
from .constraint import Constraint


class GT2(Constraint):
    id = "2T"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                for dr, dc in ((1, 0), (0, 1)):
                    pts = [(r + dr * k, c + dc * k) for k in (-1, 0, 1)]
                    if all(0 <= x < puzzle.height and 0 <= y < puzzle.width for x, y in pts):
                        total = sum_of(Lin(((mine_vars[p], 1),)) for p in pts)
                        clauses.append(Cmp(">=", total, Lin((), 1)))
                        clauses.append(Cmp("<=", total, Lin((), 2)))
        return all_of(clauses)
