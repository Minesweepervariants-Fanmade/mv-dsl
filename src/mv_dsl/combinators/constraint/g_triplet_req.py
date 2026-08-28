"""GTripletReq：必三连（[1T']）——所有雷必须处于横、竖或斜方向的三连中。

每个雷格必须属于某个直线 3 连窗口（全雷）。
对照官方 BuildMetaConstraints case "[T']"（mv2 反编译 1630-1675 行）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Not, Or, all_of
from .constraint import Constraint

_DIRS = ((1, 0), (0, 1), (1, 1), (1, -1))  # 竖、横、主对角、副对角


class GTripletReq(Constraint):
    id = "T'"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                windows: list[object] = []
                for dr, dc in _DIRS:
                    for k in (-1, 0, 1):
                        pts = [(r + dr * (k + i), c + dc * (k + i)) for i in (-1, 0, 1)]
                        if all(0 <= x < puzzle.height and 0 <= y < puzzle.width for x, y in pts):
                            windows.append(
                                all_of(BVar(mine_vars[p]) for p in pts)
                            )
                # b[pos] → 存在包含自身的直线 3 连全雷
                clauses.append(Or((Not(BVar(mine_vars[(r, c)])),) + tuple(windows)))
        return all_of(clauses)
