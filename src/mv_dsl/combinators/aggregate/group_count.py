"""AGroupCount：连续雷段数（[P] Partition）。

编码采用官方 14mv1 的**段起点计数**（`MinesweeperSolver.cs:1169-1214`）：
环形扫描中每个连续雷段的首格 = `b[d] ∧ ¬b[d-1]`，段数即这些布尔之和。
纯线性约束，替代表约束。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Lin
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
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("AGroupCount 仅支持 RelationEquals")
        # 显示值（段数 P）在编译期已知，直接约束段起点计数 == P
        p = puzzle.cells[row][col].clue.value
        return Cmp("==", group_count_lin(model, puzzle, row, col, mine_vars), Lin((), p))
