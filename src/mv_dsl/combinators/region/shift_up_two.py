"""RShiftUpTwo：3x3 去掉下三格（[2D'] Deviation' 的区域）。

区域 = 行 i-1..i × 列 j-1..j+1（上两行，共 6 格）。
对照官方 `GetSimpleClueAffectedRegion` case "[2D']"（mv2 反编译 830-843 行）。
"""

from __future__ import annotations

from .region import Region


class RShiftUpTwo(Region):
    id = "shift_up_two"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        out = []
        for r in range(row - 1, row + 1):
            for c in range(col - 1, col + 2):
                if 0 <= r < puzzle.height and 0 <= c < puzzle.width:
                    out.append((r, c))
        return out
