"""RCross：半径 2 十字（[X] Cross）。"""

from __future__ import annotations

from .region import CROSS2, Region


class RCross(Region):
    id = "cross"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        out = []
        for dr, dc in CROSS2:
            r, c = row + dr, col + dc
            if 0 <= r < puzzle.height and 0 <= c < puzzle.width:
                out.append((r, c))
        return out
