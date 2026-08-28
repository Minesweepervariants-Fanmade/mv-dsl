"""AGroupCount：连续雷段数（[P] Partition）。"""

from __future__ import annotations

from ..region.region import WALL_ORDER
from ._wall import encode_wall_table
from .aggregate import Aggregate, wall_segments_from
from ..relation.equals import RelationEquals


class AGroupCount(Aggregate):
    id = "group_count"

    def value(self, puzzle, row, col, cells, weight):
        r0, c0 = row, col
        mines = tuple(
            0 <= r < puzzle.height
            and 0 <= c < puzzle.width
            and puzzle.cells[r][c].mine
            for r, c in [(r0 + dr, c0 + dc) for dr, dc in WALL_ORDER]
        )
        return len(wall_segments_from(mines))

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("AGroupCount 仅支持 RelationEquals")
        return encode_wall_table(model, puzzle, row, col, "P", mine_vars, clue_var)
