"""RShiftUp：上移 3x3（[2D] Deviation 的区域，以正上方一格为中心）。

区域 = 行 i-2..i × 列 j-1..j+1（含自身行，共 3x3）。
对照官方 `GetSimpleClueAffectedRegion` case "[2D]"（mv2 反编译 814-829 行）。
"""

from __future__ import annotations

from .region import Region


class RShiftUp(Region):
    id = "shift_up"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        out = []
        for r in range(row - 2, row + 1):
            for c in range(col - 1, col + 2):
                if 0 <= r < puzzle.height and 0 <= c < puzzle.width:
                    out.append((r, c))
        return out
