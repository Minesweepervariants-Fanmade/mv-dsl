"""C2Bridge：桥（[2B]）——雷构成若干组桥，每组是从左端八连通相连到右端的雷。

对照官方 BuildMetaConstraints case "[2B]"（mv2 反编译 2738-2819 行）与
fanmade `Rule2B.create_constraints_xqbk`（accuracy+speed 综合最优）。

**官方实现的已知缺陷**：空隙平衡约束（list118，横向空隙 → 上方两列累计
雷数相等）只能检测「空隙处」的前缀差。当 k（每列雷数 / 桥数）≥ 4 时，
成块错位的断桥（第 i 桥相邻列行差 ≥ 2，但错位处每行都有雷挡住空隙）会被
漏检——程序枚举证明：k≤3 漏检 0（游戏最多 3 条桥，故官方从未暴露），
k=4 漏检 60 个列对，k=5 漏检 398 个。实测 9x9 反例 L4/L7 官方假 SAT。

**修复（xqbk 风格）**：对任意相邻两列 a、b 的任意两格 (ia, ib)（都非雷时）：
$$|\\text{pref}_a(ia) - \\text{pref}_b(ib)| \\le |ia - ib|$$
即「空隙点上方两列累计雷数差 ≤ 行位置差」。该约束严格强于官方空隙平衡
（ia == ib 时退化为官方情形），能捕获块错位断桥。7 布局 + 60 随机属性测试
与 nt oracle 全部一致，开放求解 39ms（官方 31ms、nt 89ms、real 55ms、
hhy 59ms，9x9 k=4）。

约束构成：
1. 方阵 + MineCount % n == 0 检查；每列雷数 == MineCount / n（列平衡）
2. 相邻列空隙前缀差约束（上方）
"""

from __future__ import annotations

from ...ir.expr import And, BVar, Cmp, Imp, Lin, Not, all_of, sum_of
from .constraint import Constraint


class C2Bridge(Constraint):
    id = "2B"

    def encode(self, model, puzzle, mine_vars):
        h, w = puzzle.height, puzzle.width
        if h != w:
            raise ValueError("[2B] Bridge 要求方阵")
        n = h
        if puzzle.mine_count is None or puzzle.mine_count % n != 0:
            raise ValueError("[2B] Bridge 要求雷数能被边长整除")
        k = puzzle.mine_count // n
        clauses = []

        # 1) 每列雷数 == k（列平衡，list122）
        for c in range(n):
            clauses.append(
                Cmp("==", sum_of(Lin(((mine_vars[(r, c)], 1),)) for r in range(n)), Lin((), k))
            )

        # 2) 相邻列空隙前缀差约束（xqbk 风格，修复官方 4 桥缺陷）：
        #    对任意两格 (ia, ib)（分别位于列 a、a+1 且都非雷），
        #    |pref_a(ia) - pref_b(ib)| <= |ia - ib|
        #    前缀和用辅助变量预计算（每列 n+1 个），空隙约束 O(1) 引用，
        #    避免 O(n³) 个独立 sum 展开导致模型膨胀。
        for a in range(n - 1):
            col_a = [mine_vars[(r, a)] for r in range(n)]
            col_b = [mine_vars[(r, a + 1)] for r in range(n)]
            pref_a = [model.new_int(f"2Bpref_a{a}_{i}", 0, n) for i in range(n + 1)]
            pref_b = [model.new_int(f"2Bpref_b{a}_{i}", 0, n) for i in range(n + 1)]
            clauses.append(Cmp("==", pref_a[0], Lin((), 0)))
            clauses.append(Cmp("==", pref_b[0], Lin((), 0)))
            for i in range(n):
                clauses.append(
                    Cmp("==", pref_a[i + 1], pref_a[i] + Lin(((col_a[i], 1),)))
                )
                clauses.append(
                    Cmp("==", pref_b[i + 1], pref_b[i] + Lin(((col_b[i], 1),)))
                )
            for ia in range(n):
                for ib in range(n):
                    gap = And((Not(BVar(col_a[ia])), Not(BVar(col_b[ib]))))
                    diff = abs(ia - ib)
                    clauses.append(
                        Imp(gap, Cmp("<=", pref_a[ia] - pref_b[ib], Lin((), diff)))
                    )
                    clauses.append(
                        Imp(gap, Cmp(">=", pref_a[ia] - pref_b[ib], Lin((), -diff)))
                    )

        return all_of(clauses)
