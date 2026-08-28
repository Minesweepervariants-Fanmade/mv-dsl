"""C2Connected：连方（[2C]）——(1) 所有四连通雷区域为矩形；(2) 所有雷区域对角相邻。

对照官方 BuildMetaConstraints case "[2C]"（mv2 反编译 2537-2560 行）：

1. [2C1] 雷区对角连通（八连通单分量）——`ActiveVerticesConnected(diagonalConnected: true)`
2. [2C2] 每个 2x2 块的雷数 != 3（否则区域非矩形）

实现：复用轻量八连通编码（CConnected 同思路）+ 2x2 线性约束。
"""

from __future__ import annotations

from ...ir.expr import And, BVar, Cmp, Imp, Lin, Not, Or, all_of, sum_of
from .constraint import Constraint

_NEIGH8 = ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))


class C2Connected(Constraint):
    id = "2C"

    def encode(self, model, puzzle, mine_vars):
        h, w = puzzle.height, puzzle.width
        n = h * w
        clauses = []

        # 1) 八连通单分量（轻量层编码，与 CConnected 相同）
        layer = {}
        for r in range(h):
            for c in range(w):
                layer[(r, c)] = model.new_int(f"c2c_{r}_{c}", 0, n)

        roots: list[object] = []
        for pos, lay in layer.items():
            r, c = pos
            b = BVar(mine_vars[pos])
            clauses.append(Imp(b, Cmp(">=", lay, Lin((), 1))))
            clauses.append(Imp(Not(b), Cmp("==", lay, Lin((), 0))))
            root = model.new_bool(f"c2c_root_{r}_{c}")
            model.add(Imp(root, Cmp("==", lay, Lin((), 1))))
            model.add(Imp(And((b, Cmp("==", lay, Lin((), 1)))), root))
            roots.append(root)

            parents = []
            for dr, dc in _NEIGH8:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w:
                    parents.append(Cmp("==", layer[(nr, nc)], lay - 1))
            if parents:
                clauses.append(
                    Imp(And((b, Not(root))), Or(tuple(parents)))
                )

        clauses.append(Cmp("==", sum_of(Lin(((r.vid, 1),)) for r in roots), Lin((), 1)))

        # 2) 2x2 块雷数 != 3
        for r in range(h - 1):
            for c in range(w - 1):
                four = sum_of(
                    Lin(((mine_vars[(r + dr, c + dc)], 1),))
                    for dr, dc in ((0, 0), (1, 0), (0, 1), (1, 1))
                )
                clauses.append(Cmp("!=", four, Lin((), 3)))

        return all_of(clauses)
