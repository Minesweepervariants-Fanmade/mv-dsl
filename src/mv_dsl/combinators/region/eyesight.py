"""REyesight：四方向视线（[E] Eyesight / [E'] Eyesight'）。

视线区域特殊：需要按方向分组（上/下/左/右），供视野类聚合子
（`AEyesight` / `ASightDiff`）做连续可见格数编码。
"""

from __future__ import annotations

from .region import Region


class REyesight(Region):
    id = "eyesight"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        """全部方向的格子（不含自身），供通用求和类聚合使用。"""
        out = []
        for group in self.directions(puzzle, row, col):
            out.extend(group)
        return out

    def directions(
        self, puzzle, row: int, col: int
    ) -> list[list[tuple[int, int]]]:
        """四方向分组，每组**由近及远**排列：上、下、左、右。"""
        up = [(r, col) for r in range(row - 1, -1, -1)]
        down = [(r, col) for r in range(row + 1, puzzle.height)]
        left = [(row, c) for c in range(col - 1, -1, -1)]
        right = [(row, c) for c in range(col + 1, puzzle.width)]
        return [up, down, left, right]
