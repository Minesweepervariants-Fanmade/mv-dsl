"""GGroupArea：雷区面积约束（[2G] 面积=4 / [2G'] 面积=3）。

每个四连通雷分量的面积恰为给定值。复用通用连通分量编码：
对每个可能的分量根 seed，若该分量非空（count>0）则面积 == 目标值。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Imp, Lin, all_of
from .connectivity import build_components
from .constraint import Constraint


class GGroupArea(Constraint):
    """参数化面积约束（area=4 → [2G]；area=3 → [2G']）。"""

    id = "2G"
    area: int = 4

    def encode(self, model, puzzle, mine_vars):
        comps = build_components(model, puzzle, mine_vars, diagonal=False)
        clauses = []
        for v in comps.values():
            clauses.append(
                Imp(Cmp(">", v["count"], Lin((), 0)), Cmp("==", v["count"], Lin((), self.area)))
            )
        return all_of(clauses)


class GGroup4(GGroupArea):
    id = "2G"
    area = 4


class GGroup3(GGroupArea):
    id = "2G'"
    area = 3
