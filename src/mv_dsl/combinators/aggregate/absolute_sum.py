"""AAbsoluteSum：加权和的绝对值 $|\\Sigma|$（[N]/[NX]/[MN] Negative 家族）。

约束编码：$|\\Sigma| = v \\iff \\Sigma = v \\lor \\Sigma = -v$。
当前仅支持 `RelationEquals`（官方 mv1 中这些规则无 Liar 组合）。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Lin, Or, sum_of
from .aggregate import Aggregate
from ..relation.equals import RelationEquals


class AAbsoluteSum(Aggregate):
    id = "absolute_sum"

    def value(self, puzzle, row, col, cells, weight):
        total = 0
        for r, c in cells:
            if puzzle.cells[r][c].mine:
                total += weight.coeff(puzzle.cells[r][c])
        return abs(total)

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError(
                "AAbsoluteSum 仅支持 RelationEquals（官方 mv1 的 Negative 家族无 Liar 组合）"
            )
        terms = [
            Lin(((mine_vars[(r, c)], weight.coeff(puzzle.cells[r][c])),))
            for r, c in cells
        ]
        total = sum_of(terms)
        # |Σ| == v ⇔ (Σ == v) ∨ (Σ == -v)
        return Or((Cmp("==", total, clue_var), Cmp("==", total, clue_var * -1)))
