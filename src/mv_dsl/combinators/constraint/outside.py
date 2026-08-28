"""COutside：外部（[1O]）——非雷区域四连通；每个雷区域以四连通连接到题版边界。

对照官方 BuildMetaConstraints case "[1O]"（mv2 反编译 2315-2370 行）：

1. 非雷区四连通（ActiveVerticesConnected(~isBomb)）——非雷只构成一个四连通分量
2. 每个雷分量接触边界（OutsideConnection）——用分量 id 体系：每雷分量存在边界雷
3. 2x2 对角模式禁止（list83）——`¬(b00∧¬b10∧¬b01∧b11)` 与 `¬(¬b00∧b10∧b01∧¬b11)`
"""

from __future__ import annotations

from ...ir.expr import BVar, Cmp, Imp, Lin, Not, Or, all_of, sum_of
from .constraint import Constraint
from .connectivity import build_components

_NEIGH4 = ((0, 1), (1, 0), (0, -1), (-1, 0))


class COutside(Constraint):
    id = "O"

    def encode(self, model, puzzle, mine_vars):
        h, w = puzzle.height, puzzle.width
        clauses = []

        # 1) 2x2 对角模式禁止（list83）：禁止「对角雷 + 另一对角非雷」
        for r in range(h - 1):
            for c in range(w - 1):
                b00 = BVar(mine_vars[(r, c)])
                b10 = BVar(mine_vars[(r + 1, c)])
                b01 = BVar(mine_vars[(r, c + 1)])
                b11 = BVar(mine_vars[(r + 1, c + 1)])
                clauses.append(Or((Not(b00), b10, b01, Not(b11))))
                clauses.append(Or((b00, Not(b10), Not(b01), b11)))

        # 2) 非雷区四连通（单分量）：非雷分量体系 + 恰一个根
        safe = build_components(model, puzzle, mine_vars, diagonal=False, active_mine=False)
        roots = [v["root"] for v in safe.values()]
        clauses.append(Cmp("==", sum_of(Lin(((r.vid, 1),)) for r in roots), Lin((), 1)))

        # 3) 每个雷分量接触边界：**雷分量**体系，每雷格的分量存在边界雷
        mines = build_components(model, puzzle, mine_vars, diagonal=False)
        def is_edge(r, c):
            return r == 0 or c == 0 or r == h - 1 or c == w - 1

        edge_mines = [(r, c) for r in range(h) for c in range(w) if is_edge(r, c)]
        for pos, v in mines.items():
            # 同分量判断用 id 相等（分量内所有格 id 相同，非根格 id == 根 seed）
            touch = Or(
                tuple(
                    Cmp("==", mines[q]["id"], v["id"])
                    for q in edge_mines
                )
            )
            clauses.append(Imp(BVar(mine_vars[pos]), touch))

        return all_of(clauses)
