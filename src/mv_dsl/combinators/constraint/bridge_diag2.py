"""C2BridgeDiag：斜桥（[2B']）——雷构成若干组链，每组是从左端斜角相连到右端的雷。

对照官方 BuildMetaConstraints case "[2B']"（mv2 反编译 2821-2920 行）：

1. MineCount % SizeX == 0；每列颜色 c 的雷数分别相等（list131）：
   颜色 0（(x+y)%2==0）各列雷数 == intVar、颜色 1 各列 == intVar2，intVar+intVar2==K
2. 每个雷斜向上（左上/右上）或斜向下（左下/右下）至少一个雷（list124）
3. 纵向空隙（同色格 (x,y),(x,y-1) 都非雷）→ 左侧同色两行的雷数相等（list127）
"""

from __future__ import annotations

from ...ir.expr import And, BVar, Cmp, Imp, Lin, Not, Or, all_of, sum_of
from .constraint import Constraint


class C2BridgeDiag(Constraint):
    id = "2B'"

    def encode(self, model, puzzle, mine_vars):
        h, w = puzzle.height, puzzle.width
        if h != w:
            raise ValueError("[2B'] Bridge' 要求方阵")
        n = h
        if puzzle.mine_count is None or puzzle.mine_count % n != 0:
            raise ValueError("[2B'] Bridge' 要求雷数能被边长整除")
        k = puzzle.mine_count // n
        clauses = []

        def color(c, r):
            return (c + r) % 2

        # 1) 每列颜色 c 雷数 == 对应变量（两色各自列间相等）
        col0 = model.new_int("2bd_col0", 0, k)
        col1 = model.new_int("2bd_col1", 0, k)
        model.add(Cmp("==", col0 + col1, Lin((), k)))
        for c in range(n):
            cnt0 = sum_of(
                Lin(((mine_vars[(r, c)], 1),)) for r in range(n) if color(c, r) == 0
            )
            cnt1 = sum_of(
                Lin(((mine_vars[(r, c)], 1),)) for r in range(n) if color(c, r) == 1
            )
            clauses.append(Cmp("==", cnt0, col0))
            clauses.append(Cmp("==", cnt1, col1))

        # 2) 每雷斜向上或斜向下至少一个雷（界内）
        for r in range(n):
            for c in range(n):
                up = [
                    mine_vars[(r - 1, c + dc)]
                    for dc in (-1, 1)
                    if 0 <= r - 1 < n and 0 <= c + dc < n
                ]
                down = [
                    mine_vars[(r + 1, c + dc)]
                    for dc in (-1, 1)
                    if 0 <= r + 1 < n and 0 <= c + dc < n
                ]
                clauses.append(
                    Imp(
                        BVar(mine_vars[(r, c)]),
                        Or(tuple(BVar(v) for v in up + down)),
                    )
                )

        # 3) 横向空隙（同色格 (行y,列x) 与 (行y,列x-1) 都非雷）→ 上方（行<y）
        #    的列 x 与列 x-1 的**同色**雷数相等（list127）
        for c0 in range(2):
            for y in range(1, n):
                for x in range(1, n):
                    cond_terms = []
                    if color(x, y) == c0:
                        cond_terms.append(Not(BVar(mine_vars[(y, x)])))
                    if color(x, y - 1) == c0:
                        cond_terms.append(Not(BVar(mine_vars[(y, x - 1)])))
                    if not cond_terms:
                        continue
                    up_x = sum_of(
                        Lin(((mine_vars[(r, x)], 1),))
                        for r in range(y)
                        if color(x, r) == c0
                    )
                    up_xm1 = sum_of(
                        Lin(((mine_vars[(r, x - 1)], 1),))
                        for r in range(y)
                        if color(x - 1, r) == c0
                    )
                    clauses.append(
                        Imp(And(tuple(cond_terms)), Cmp("==", up_x, up_xm1))
                    )

        return all_of(clauses)
