"""A2Cross：双色计数，顺序不确定（[2X] Cross）。

值编码：`10 × 染色雷数 + 非染色雷数`（官方 token 如 `2x34` → 染色 3、非染色 4）。
约束：显示值拆为 (a, b)，(染色==a ∧ 非染色==b) ∨ (染色==b ∧ 非染色==a)。
对照官方 `GetCellConstraint` case "[2X]"（mv2 反编译 3494-3514 行）。
"""

from __future__ import annotations

from ...ir.expr import And, Cmp, Lin, Or
from .aggregate import Aggregate
from ..relation.equals import RelationEquals
from ..relation.encrypted import RelationEncrypted, perm_value


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
        shown = puzzle.cells[row][col].clue.value
        a, b = shown // 10, shown % 10

        colored_lin = Lin()
        uncolored_lin = Lin()
        for r, c in cells:
            if puzzle.cells[r][c].colored:
                colored_lin = colored_lin + Lin(((mine_vars[(r, c)], 1),))
            else:
                uncolored_lin = uncolored_lin + Lin(((mine_vars[(r, c)], 1),))
        total_lin = colored_lin + uncolored_lin

        from ..relation.offset import RelationOffset

        if isinstance(relation, RelationOffset):
            # [2LX-]（官方 mv2 反编译 4281-4309）：显示值已归一化为 num77。
            # 总雷数 == (a+b) ± 1（误差方向未知），且染色或非染色 ∈ {a, b}。
            cond = [Cmp("==", colored_lin, Lin((), a)), Cmp("==", uncolored_lin, Lin((), a))]
            if a != b:
                cond += [Cmp("==", colored_lin, Lin((), b)), Cmp("==", uncolored_lin, Lin((), b))]
            total_ok = Or(
                (Cmp("==", total_lin, Lin((), a + b + 1)), Cmp("==", total_lin, Lin((), a + b - 1)))
            )
            return And((Or(tuple(cond)), total_ok))

        if isinstance(relation, RelationEncrypted):
            # [2EX]：显示值 10a+b 的两个数字均为加密索引 → 解密为真实值
            from ..relation.encrypted import perm_value

            ra, rb = perm_value(model, puzzle, a), perm_value(model, puzzle, b)
            return Or(
                (
                    And((Cmp("==", colored_lin, ra), Cmp("==", uncolored_lin, rb))),
                    And((Cmp("==", colored_lin, rb), Cmp("==", uncolored_lin, ra))),
                )
            )
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError(f"A2Cross 不支持 {type(relation).__name__}")

        return Or(
            (
                And((Cmp("==", colored_lin, Lin((), a)), Cmp("==", uncolored_lin, Lin((), b)))),
                And((Cmp("==", colored_lin, Lin((), b)), Cmp("==", uncolored_lin, Lin((), a)))),
            )
        )
