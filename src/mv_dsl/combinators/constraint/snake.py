"""CSnake：蛇（[1S]）——所有雷构成一条宽度为 1 的四连通路径，无分叉、环、交叉。

对照官方 BuildMetaConstraints case "[1S]"（mv2 反编译 1820-1862 行）：

1. 每个雷：4 邻雷数 ∈ [1, 2]（无孤立、无分叉）
2. 4 邻雷数 == 1 的雷（端点）恰有 2 个
3. 雷区四连通（单分量，四邻）
"""

from __future__ import annotations

from ...ir.expr import (
    And,
    BVar,
    Cmp,
    Iff,
    Imp,
    Lin,
    Not,
    Or,
    all_of,
    sum_of,
)
from .constraint import Constraint
from .connectivity import build_components

_NEIGH4 = ((0, 1), (1, 0), (0, -1), (-1, 0))


class CSnake(Constraint):
    id = "S"

    def encode(self, model, puzzle, mine_vars):
        h, w = puzzle.height, puzzle.width
        clauses = []

        # 1) 雷区四连通单分量
        comps = build_components(model, puzzle, mine_vars, diagonal=False)
        roots = [v["root"] for v in comps.values()]
        clauses.append(Cmp("==", sum_of(Lin(((r.vid, 1),)) for r in roots), Lin((), 1)))

        # 2) 度数约束：每雷 4 邻雷数 ∈ [1,2]；端点（度==1）总数 == 2
        endpoints: list[object] = []
        for r in range(h):
            for c in range(w):
                b = BVar(mine_vars[(r, c)])
                deg = sum_of(
                    Lin(((mine_vars[(r + dr, c + dc)], 1),))
                    for dr, dc in _NEIGH4
                    if 0 <= r + dr < h and 0 <= c + dc < w
                )
                clauses.append(Imp(b, Cmp(">=", deg, Lin((), 1))))
                clauses.append(Imp(b, Cmp("<=", deg, Lin((), 2))))
                endp = model.new_bool(f"snake_end_{r}_{c}")
                model.add(Iff(endp, And((b, Cmp("==", deg, Lin((), 1))))))
                endpoints.append(endp)

        clauses.append(
            Cmp("==", sum_of(Lin(((e.vid, 1),)) for e in endpoints), Lin((), 2))
        )

        return all_of(clauses)
