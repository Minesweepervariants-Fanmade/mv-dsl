"""RKnight：马步 8 格（[K] Knight）。"""

from __future__ import annotations

from .region import KNIGHT, Region


class RKnight(Region):
    id = "knight"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        out = []
        for dr, dc in KNIGHT:
            r, c = row + dr, col + dc
            if 0 <= r < puzzle.height and 0 <= c < puzzle.width:
                out.append((r, c))
        return out
