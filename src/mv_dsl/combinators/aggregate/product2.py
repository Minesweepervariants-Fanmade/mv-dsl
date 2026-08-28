"""A2Product：距离最近的 2 个雷的距离之积（[2P] Product / [2EP] Encrypted Product）。

距离用**欧氏距离平方**（官方 `(k-i)²+(l-j)²`）。token 值 = 两个平方距离的积
（如距离 1、2 的雷 → 1×4=4，显示时开方为 2，对照 legacy `simple_sqrt`）。

约束（官方 `DistProductCondition`，mv2 反编译 3166-3235 行）：
∃ 两格 a（距离² d1）、b（距离² d2）为雷，d1×d2 == 显示值，且
除 a 外所有距离² < d2 的格非雷（a、b 是**最近的两个**雷）。

[2EP]（RelationEncrypted(square=True)）：显示值为加密索引，
- < 50：距离积 == 置换[索引]²（开方显示，官方 :4060 逐行绑定 num32²）
- >= 50：距离积 == 置换[索引-50]（√ 前缀显示，官方 :4051 逐行绑定 num31）
求解模式（副板变量）下平方分支无法线性化，用官方「逐行绑定」：
副板第 idx 列每行 r 有雷 ⟺ 距离积 == r²（或 r）。
"""

from __future__ import annotations

from ...ir.expr import And, BConst, BVar, Cmp, Iff, Not, Or, all_of
from .aggregate import Aggregate
from ..relation.equals import RelationEquals
from ..relation.encrypted import RelationEncrypted, permutation_from_puzzle


class A2Product(Aggregate):
    id = "2product"

    def value(self, puzzle, row, col, cells, weight):
        dists: list[tuple[int, tuple[int, int]]] = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                if puzzle.cells[r][c].mine and (r, c) != (row, col):
                    d = (r - row) * (r - row) + (c - col) * (c - col)
                    dists.append((d, (r, c)))
        dists.sort()
        if len(dists) < 2:
            return 0
        return dists[0][0] * dists[1][0]

    def _dist_product_expr(self, model, puzzle, row, col, mine_vars, target: int):
        """距离积 == target 的约束表达式。target == 0 时要求自身非雷（无两雷）。"""
        if target == 0:
            return Not(BVar(mine_vars[(row, col)]))

        # 距离² → 该距离的格集合（含自身除外）
        by_dist: dict[int, list[tuple[int, int]]] = {}
        dists: list[int] = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                if (r, c) == (row, col):
                    continue
                d = (r - row) * (r - row) + (c - col) * (c - col)
                if d not in by_dist:
                    by_dist[d] = []
                    dists.append(d)
                by_dist[d].append((r, c))
        dists.sort()

        cases: list[object] = []
        for d1 in dists:
            if target % d1 != 0:
                continue
            d2 = target // d1
            if d2 < d1 or d2 not in by_dist:
                continue
            for a in by_dist[d1]:
                for b in by_dist[d2]:
                    if a == b:
                        continue
                    literals: list[object] = [BVar(mine_vars[a]), BVar(mine_vars[b])]
                    # 除 a 外，所有距离² < d2 的格非雷（保证 a、b 是最近的两个）
                    for d in dists:
                        if d >= d2:
                            break
                        for g in by_dist[d]:
                            if g != a:
                                literals.append(Not(BVar(mine_vars[g])))
                    cases.append(all_of(literals))

        # 无可行因子对 → 恒假（Or 空列表由 any_of 折叠为 BConst(False)）
        return Or(tuple(cases))

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        shown = puzzle.cells[row][col].clue.value
        from ..relation.offset import RelationOffset

        if isinstance(relation, RelationOffset):
            # [2LP-]（官方 mv2 反编译 4311-4335）：显示值 num77。
            # 完全平方 → 距离积 ∈ {(√-1)², (√+1)²}；否则距离积 == 显示值。
            import math

            s = math.isqrt(shown)
            if s * s == shown:
                return Or(
                    (
                        self._dist_product_expr(model, puzzle, row, col, mine_vars, (s - 1) * (s - 1)),
                        self._dist_product_expr(model, puzzle, row, col, mine_vars, (s + 1) * (s + 1)),
                    )
                )
            return self._dist_product_expr(model, puzzle, row, col, mine_vars, shown)
        if isinstance(relation, RelationEncrypted):
            idx = shown - 50 if shown >= 50 else shown
            square = shown < 50
            perm_cells = model.extras.get("perm_cells")
            if perm_cells is not None:
                # 求解模式：逐行绑定副板格 == (距离积 == r² / r)。
                # target == 0 时官方 DistProductCondition(0) == false（恒假）——
                # 注意与 2P 本体 token 0 的「无两雷」（自身非雷）语义不同。
                conds = []
                for r in range(puzzle.height):
                    target = r * r if square else r
                    if target == 0:
                        expr_b = BConst(False)
                    else:
                        expr_b = self._dist_product_expr(model, puzzle, row, col, mine_vars, target)
                    conds.append(
                        Iff(
                            BVar(perm_cells[(idx, r)]),
                            expr_b,
                        )
                    )
                return all_of(conds)
            # 验证模式：置换固定
            enc = permutation_from_puzzle(puzzle)
            r = enc[idx]
            target = r * r if square else r
            return self._dist_product_expr(model, puzzle, row, col, mine_vars, target)
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError(f"A2Product 不支持 {type(relation).__name__}")
        return self._dist_product_expr(model, puzzle, row, col, mine_vars, shown)
