"""RFull：全盘区域（[2P] Product 等动态规则的区域占位）。"""

from __future__ import annotations

from .region import Region


class RFull(Region):
    id = "full"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        return [
            (r, c)
            for r in range(puzzle.height)
            for c in range(puzzle.width)
            if (r, c) != (row, col)
        ]
