"""GConnected：八连通（[1C]）——所有雷构成一个八连通区域。

用通用连通分量编码 + 「至多一个非空分量」约束。
官方用 `Graph.ActiveVerticesConnected(isBomb, diagonal: true)`（csugar 图约束）。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Imp, Lin, all_of
from .connectivity import build_components
from .constraint import Constraint


class GConnected(Constraint):
    id = "C"

    def encode(self, model, puzzle, mine_vars):
        comps = build_components(model, puzzle, mine_vars, diagonal=True)
        # 至多一个非空分量：任意两个分量不同时面积 > 0
        positions = list(comps.keys())
        clauses = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                clauses.append(
                    Imp(
                        Cmp(">", comps[positions[i]]["count"], Lin((), 0)),
                        Cmp("==", comps[positions[j]]["count"], Lin((), 0)),
                    )
                )
        return all_of(clauses) if clauses else Cmp("==", Lin((), 0), Lin((), 0))
