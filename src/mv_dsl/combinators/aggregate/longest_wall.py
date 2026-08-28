"""ALongestWall：最长连续雷段（[W'] Longest Wall）。"""

from __future__ import annotations

from ..region.region import WALL_ORDER
from ._wall import encode_wall_table
from .aggregate import Aggregate, wall_segments_from
from ..relation.equals import RelationEquals


class ALongestWall(Aggregate):
    id = "longest_wall"

    def value(self, puzzle, row, col, cells, weight):
        r0, c0 = row, col
        mines = tuple(
            0 <= r < puzzle.height
            and 0 <= c < puzzle.width
            and puzzle.cells[r][c].mine
            for r, c in [(r0 + dr, c0 + dc) for dr, dc in WALL_ORDER]
        )
        segments = wall_segments_from(mines)
        return segments[-1] if segments else 0

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("ALongestWall 仅支持 RelationEquals")
        return encode_wall_table(model, puzzle, row, col, "W'", mine_vars, clue_var)
