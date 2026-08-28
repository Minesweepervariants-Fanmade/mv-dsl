"""A2Product：距离最近的 2 个雷的距离之积（[2P] Product）。

距离用**欧氏距离平方**（官方 `(k-i)²+(l-j)²`）。token 值 = 两个平方距离的积
（如距离 1、2 的雷 → 1×4=4，显示时开方为 2，对照 legacy `simple_sqrt`）。

约束（官方 `DistProductCondition`，mv2 反编译 3166-3235 行）：
∃ 两格 a（距离² d1）、b（距离² d2）为雷，d1×d2 == 显示值，且
除 a 外所有距离² < d2 的格非雷（a、b 是**最近的两个**雷）。
"""

from __future__ import annotations

from ...ir.expr import And, BVar, Cmp, Not, Or, all_of
from .aggregate import Aggregate
from ..relation.equals import RelationEquals


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

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("A2Product 仅支持 RelationEquals")
        num = puzzle.cells[row][col].clue.value
        if num == 0:
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
            if num % d1 != 0:
                continue
            d2 = num // d1
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
