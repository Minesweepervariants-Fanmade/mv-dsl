"""A2CrossEither：染色**或**非染色格的雷数（[2X'] Cross'）。

约束：`(染色雷数 == v) ∨ (非染色雷数 == v)`——玩家不知道是哪一种。
对照官方 `GetCellConstraint` case "[2X']"（mv2 反编译 3472-3493 行）。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Lin, Or
from .aggregate import Aggregate
from ..relation.equals import RelationEquals


class A2CrossEither(Aggregate):
    id = "2cross_either"

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
        # 显示值只给其中一个数，无法确定是染色还是非染色 → 返回元组
        return self._counts(puzzle, row, col, cells, weight)

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("A2CrossEither 仅支持 RelationEquals")
        shown = puzzle.cells[row][col].clue.value

        colored_lin = Lin()
        uncolored_lin = Lin()
        for r, c in cells:
            if puzzle.cells[r][c].colored:
                colored_lin = colored_lin + Lin(((mine_vars[(r, c)], 1),))
            else:
                uncolored_lin = uncolored_lin + Lin(((mine_vars[(r, c)], 1),))

        return Or(
            (
                Cmp("==", colored_lin, Lin((), shown)),
                Cmp("==", uncolored_lin, Lin((), shown)),
            )
        )
