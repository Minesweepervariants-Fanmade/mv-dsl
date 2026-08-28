"""GTriplet：无三连（[1T]）——雷在横、竖、斜方向不能构成三连。

每个 3 连窗口至多 2 雷。对照官方 BuildMetaConstraints case "[1T]"
（mv2 反编译 1580-1629 行）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Lin, Cmp, all_of, sum_of
from .constraint import Constraint


_TRIPLES = (
    ((-1, -1), (0, 0), (1, 1)),
    ((-1, 1), (0, 0), (1, -1)),
    ((-1, 0), (0, 0), (1, 0)),
    ((0, -1), (0, 0), (0, 1)),
)


class GTriplet(Constraint):
    id = "T"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                for deltas in _TRIPLES:
                    pts = [(r + dr, c + dc) for dr, dc in deltas]
                    if all(0 <= x < puzzle.height and 0 <= y < puzzle.width for x, y in pts):
                        clauses.append(
                            Cmp("<=", sum_of(Lin(((mine_vars[p], 1),)) for p in pts), Lin((), 2))
                        )
        return all_of(clauses)
