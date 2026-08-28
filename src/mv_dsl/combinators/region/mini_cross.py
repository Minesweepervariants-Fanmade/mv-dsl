"""RMiniCross：半径 1 十字（[X'] Mini Cross）。"""

from __future__ import annotations

from .region import CROSS1, Region


class RMiniCross(Region):
    id = "mini_cross"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        out = []
        for dr, dc in CROSS1:
            r, c = row + dr, col + dc
            if 0 <= r < puzzle.height and 0 <= c < puzzle.width:
                out.append((r, c))
        return out
