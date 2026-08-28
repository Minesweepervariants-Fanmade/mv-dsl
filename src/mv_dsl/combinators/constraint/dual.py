"""GDual：对偶（[1D]）——每个雷区为 1x2 或 2x1 的矩形。

官方实现：每个雷格恰有 1 个正交邻雷。
对照官方 BuildMetaConstraints case "[1D]"（mv2 反编译 1269-1290 行）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Cmp, Lin, Or, all_of, sum_of
from .constraint import Constraint


class CDual(Constraint):
    id = "D"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                neighbors = []
                for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width:
                        neighbors.append(mine_vars[(nr, nc)])
                total = sum_of(Lin(((v, 1),)) for v in neighbors)
                clauses.append(
                    Or(
                        (
                            Not(BVar(mine_vars[(r, c)])),
                            Cmp("==", total, Lin((), 1)),
                        )
                    )
                )
        return all_of(clauses)
