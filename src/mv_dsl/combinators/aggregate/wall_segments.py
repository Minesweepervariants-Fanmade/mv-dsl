"""AWallSegments：数墙段长序列（[W] Wall）。

值为升序段长的十进制拼接（如段长 1,2,3 → `123`），与官方显示一致。
约束用邻域表约束（见 `_wall.py`）。
"""

from __future__ import annotations

from ..region.region import WALL_ORDER
from ._wall import encode_wall_table
from .aggregate import Aggregate, wall_segments_from
from ..relation.equals import RelationEquals


class AWallSegments(Aggregate):
    id = "wall_segments"

    def value(self, puzzle, row, col, cells, weight):
        r0, c0 = row, col
        mines = tuple(
            0 <= r < puzzle.height
            and 0 <= c < puzzle.width
            and puzzle.cells[r][c].mine
            for r, c in [(r0 + dr, c0 + dc) for dr, dc in WALL_ORDER]
        )
        segments = wall_segments_from(mines)
        return segments if segments else (0,)

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("AWallSegments 仅支持 RelationEquals")
        return encode_wall_table(model, puzzle, row, col, "W", mine_vars, clue_var)
