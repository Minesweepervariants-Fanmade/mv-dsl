"""GConnected：八连通（[1C]）——所有雷构成一个八连通区域。

**轻量单树编码**（对比实验结论：完整分量编码太重，慢官方 propagator 100 倍）：

- 每格一个层变量 layer ∈ [0, n²]（layer==0 ⟺ 非雷）
- 恰一个根（layer==1）
- 非根雷格存在八邻 layer == layer-1（层递减链保证连通）

无分量 id、无面积计数——单分量场景的最小编码。
官方用 `graph-active-vertices-connected`（Tarjan 传播器，6-7ms/关）；
本编码 CP-SAT 约几百 ms/关，差距来自「显式编码 vs 定制传播器」。
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

_NEIGH8 = ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))



from .constraint import Constraint


class GConnected(Constraint):
    id = "C"

    def encode(self, model, puzzle, mine_vars):
        n = puzzle.width * puzzle.height
        layer = {}
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                layer[(r, c)] = model.new_int(f"cl_{r}_{c}", 0, n)

        roots: list[object] = []
        clauses = []
        for pos, lay in layer.items():
            r, c = pos
            b = BVar(mine_vars[pos])
            # layer==0 ⟺ 非雷；layer≥1 ⟺ 雷
            clauses.append(Iff(b, Cmp(">=", lay, Lin((), 1))))
            root = model.new_bool(f"croot_{r}_{c}")
            model.add(Iff(root, Cmp("==", lay, Lin((), 1))))
            roots.append(root)

            # 非根雷 → 存在八邻 layer == layer-1
            parents = []
            for dr, dc in _NEIGH8:
                nr, nc = r + dr, c + dc
                if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width:
                    parents.append(Cmp("==", layer[(nr, nc)], lay - 1))
            if parents:
                clauses.append(
                    Imp(
                        And((b, Not(root))),
                        Or(tuple(parents)),
                    )
                )

        # 恰一个根：Σ roots == 1（线性计数替代 O(n²) 两两互斥）
        clauses.append(
            Cmp("==", sum_of(Lin(((r.vid, 1),)) for r in roots), Lin((), 1))
        )
        return all_of(clauses)
