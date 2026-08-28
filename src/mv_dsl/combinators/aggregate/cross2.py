"""A2Cross：双色计数，顺序不确定（[2X] Cross）。

值编码：`10 × 染色雷数 + 非染色雷数`（官方 token 如 `2x34` → 染色 3、非染色 4）。
约束：显示值拆为 (a, b)，(染色==a ∧ 非染色==b) ∨ (染色==b ∧ 非染色==a)。
对照官方 `GetCellConstraint` case "[2X]"（mv2 反编译 3494-3514 行）。
"""

from __future__ import annotations

from ...ir.expr import And, Cmp, Lin, Or
from .aggregate import Aggregate
from ..relation.equals import RelationEquals


class A2Cross(Aggregate):
    id = "2cross"

    def _counts(self, puzzle, row, col, cells, weight):
        colored = uncolored = 0
        for r, c in cells:
            if puzzle.cells[r][c].mine:
                if puzzle.cells[r][c].colored:
                    colored += 1
                else:
                    uncolored += 1
        return colored, uncolored

    def value(self, puzzle, row, col, cells, weight):
        colored, uncolored = self._counts(puzzle, row, col, cells, weight)
        return colored * 10 + uncolored

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("A2Cross 仅支持 RelationEquals")
        shown = puzzle.cells[row][col].clue.value
        a, b = shown // 10, shown % 10

        colored_lin = Lin()
        uncolored_lin = Lin()
        for r, c in cells:
            if puzzle.cells[r][c].colored:
                colored_lin = colored_lin + Lin(((mine_vars[(r, c)], 1),))
            else:
                uncolored_lin = uncolored_lin + Lin(((mine_vars[(r, c)], 1),))

        return Or(
            (
                And((Cmp("==", colored_lin, Lin((), a)), Cmp("==", uncolored_lin, Lin((), b)))),
                And((Cmp("==", colored_lin, Lin((), b)), Cmp("==", uncolored_lin, Lin((), a)))),
            )
        )
