"""AGroupCount：连续雷段数（[P] Partition）。

编码采用官方 14mv1 的**段起点计数**（`MinesweeperSolver.cs:1169-1214`）：
环形扫描中每个连续雷段的首格 = `b[d] ∧ ¬b[d-1]`，段数即这些布尔之和。
纯线性约束，替代表约束。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Lin, Or
from ..region.region import WALL_ORDER
from ._wall import group_count_lin
from .aggregate import Aggregate, wall_segments_from
from ..relation.equals import RelationEquals


class AGroupCount(Aggregate):
    id = "group_count"

    def value(self, puzzle, row, col, cells, weight):
        mines = tuple(
            0 <= r < puzzle.height
            and 0 <= c < puzzle.width
            and puzzle.cells[r][c].mine
            for r, c in [(row + dr, col + dc) for dr, dc in WALL_ORDER]
        )
        return len(wall_segments_from(mines))

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        from ..relation.encrypted import RelationEncrypted, perm_value
        from ..relation.offset import RelationOffset

        gc = group_count_lin(model, puzzle, row, col, mine_vars)
        # 显示值（段数 P）在编译期已知，直接约束段起点计数 == P
        if isinstance(relation, RelationEncrypted):
            # [2E1P]：段数 == 置换[显示]
            target = perm_value(model, puzzle, puzzle.cells[row][col].clue.value)
            return Cmp("==", gc, target)
        if isinstance(relation, RelationOffset):
            # [2L1P-]：段数 == 显示 ± 1（误差方向未知）
            d = puzzle.cells[row][col].clue.value
            return Or(
                (Cmp("==", gc, Lin((), d + 1)), Cmp("==", gc, Lin((), d - 1)))
            )
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError(f"AGroupCount 不支持 {type(relation).__name__}")
        p = puzzle.cells[row][col].clue.value
        return Cmp("==", gc, Lin((), p))
