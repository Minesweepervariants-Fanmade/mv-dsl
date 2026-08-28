"""CBattleship：战舰（[1D']）——每个雷区域为宽度 1、长度 ≤4 的矩形，矩形不能对角相邻。

对照官方 mv1 源码（MinesweeperSolver.cs case "[D']" 624-677 行）：
每个雷格满足：

1. `(左右邻全非雷 ∨ 上下邻全非雷)`——宽度 1（不拐弯）
2. 所有对角邻居全非雷——矩形不能对角相邻
3. 无 5 连：任意横向/纵向 5 连窗口不全雷——长度 ≤ 4
"""

from __future__ import annotations

from ...ir.expr import And, BVar, Cmp, Imp, Lin, Not, Or, all_of, sum_of
from .constraint import Constraint

_NEIGH4 = ((0, 1), (1, 0), (0, -1), (-1, 0))
_DIAG8 = ((1, 1), (1, -1), (-1, 1), (-1, -1))


class CBattleship(Constraint):
    id = "D'"

    def encode(self, model, puzzle, mine_vars):
        h, w = puzzle.height, puzzle.width
        clauses = []

        for r in range(h):
            for c in range(w):
                b = BVar(mine_vars[(r, c)])

                # 1) 左右邻全非雷 或 上下邻全非雷（宽度 1）
                horiz = [
                    Not(BVar(mine_vars[(r, c + dc)]))
                    for dc in (-1, 1)
                    if 0 <= c + dc < w
                ]
                vert = [
                    Not(BVar(mine_vars[(r + dr, c)]))
                    for dr in (-1, 1)
                    if 0 <= r + dr < h
                ]
                # 14mv 方阵最小 5x5，角落格也有邻居；空列表意味着该侧恒满足
                if horiz and vert:
                    straight = Or((And(tuple(horiz)), And(tuple(vert))))
                elif horiz:
                    straight = And(tuple(horiz))
                else:
                    straight = And(tuple(vert))

                # 2) 对角邻居全非雷
                diag_safe = [
                    Not(BVar(mine_vars[(r + dr, c + dc)]))
                    for dr, dc in _DIAG8
                    if 0 <= r + dr < h and 0 <= c + dc < w
                ]

                clauses.append(Imp(b, And((straight, And(tuple(diag_safe))))))

        # 3) 无 5 连（横向/纵向窗口 sum ≤ 4）
        for r in range(h):
            for c in range(w - 4):
                clauses.append(
                    Cmp(
                        "<=",
                        sum_of(Lin(((mine_vars[(r, c + k)], 1),)) for k in range(5)),
                        Lin((), 4),
                    )
                )
        for c in range(w):
            for r in range(h - 4):
                clauses.append(
                    Cmp(
                        "<=",
                        sum_of(Lin(((mine_vars[(r + k, c)], 1),)) for k in range(5)),
                        Lin((), 4),
                    )
                )

        return all_of(clauses)
