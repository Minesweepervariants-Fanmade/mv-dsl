"""RMoore：3x3 九宫（[V] Vanilla 及多数线索规则的区域）。"""

from __future__ import annotations

from .region import NEIGH8, Region


class Rstd(Region):
    id = "std"

    def cells(self, puzzle, row: int, col: int) -> list[tuple[int, int]]:
        out = []
        for dr, dc in NEIGH8:
            r, c = row + dr, col + dc
            if 0 <= r < puzzle.height and 0 <= c < puzzle.width:
                out.append((r, c))
        return out
