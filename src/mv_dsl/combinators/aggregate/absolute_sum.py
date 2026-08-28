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
        from ..relation.encrypted import RelationEncrypted, perm_value
        from ..relation.offset import RelationOffset

        terms = [
            Lin(((mine_vars[(r, c)], weight.coeff(puzzle.cells[r][c])),))
            for r, c in cells
        ]
        total = sum_of(terms)
        if isinstance(relation, RelationEncrypted):
            # [2E1N]：|Σ| == 置换[显示] ⇔ Σ == ±置换[显示]
            target = perm_value(model, puzzle, puzzle.cells[row][col].clue.value)
            return Or((Cmp("==", total, target), Cmp("==", total, target * -1)))
        if isinstance(relation, RelationOffset):
            # [2L1N-]：|Σ| == 显示 ± 1 ⇔ Σ == ±(显示±1)
            d = puzzle.cells[row][col].clue.value
            return Or(
                (
                    Cmp("==", total, Lin((), d + 1)),
                    Cmp("==", total, Lin((), -d - 1)),
                    Cmp("==", total, Lin((), d - 1)),
                    Cmp("==", total, Lin((), -d + 1)),
                )
            )
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError(
                f"AAbsoluteSum 不支持 {type(relation).__name__}"
            )
        # |Σ| == v ⇔ (Σ == v) ∨ (Σ == -v)
        return Or((Cmp("==", total, clue_var), Cmp("==", total, clue_var * -1)))
