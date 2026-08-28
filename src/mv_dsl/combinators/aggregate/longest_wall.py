"""ALongestWall：最长连续雷段（[W'] Longest Wall）。

编码为**窗口布尔组合**，无表约束：
- 最长段 ≤ w ⟺ 每个 (w+1)-连续窗口至少一个非雷（含越界）
- 最长段 ≥ w ⟺ 存在 w 连续全雷窗口
"""

from __future__ import annotations

from ..region.region import WALL_ORDER
from ._wall import longest_wall_bool
from .aggregate import Aggregate, wall_segments_from
from ..relation.equals import RelationEquals


class ALongestWall(Aggregate):
    id = "longest_wall"

    def value(self, puzzle, row, col, cells, weight):
        mines = tuple(
            0 <= r < puzzle.height
            and 0 <= c < puzzle.width
            and puzzle.cells[r][c].mine
            for r, c in [(row + dr, col + dc) for dr, dc in WALL_ORDER]
        )
        segments = wall_segments_from(mines)
        return segments[-1] if segments else 0

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("ALongestWall 仅支持 RelationEquals")
        w = puzzle.cells[row][col].clue.value  # 最长段在编译期已知
        return longest_wall_bool(model, puzzle, row, col, w, mine_vars)
