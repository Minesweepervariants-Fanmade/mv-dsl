"""连通分量编码（通用基础设施，供 2A/1C/2G/2G' 等连通类规则共享）。

对每个雷格引入分量 id 与 BFS 层，使分量连通且每分量恰有一个根（层 0）：

- `id[p]` ∈ [0, n²]：分量编号。**根的分量 id = 自身 seed**（保证唯一），
  非根的分量 id > 自身 seed。非雷格 id = 0。
- `layer[p]` ∈ [0, n²]：BFS 层。根 = 0；非根雷格存在邻居层 = layer-1
  （层递减链保证连通到根）。
- 相邻雷格同分量（id 相等）——不同分量的雷对角相邻时 id 不同。

约束构成（参照 fanmade `Rrule/2A.py` 的 id+step 编码思路，自研实现）：

1. 非雷 → id=0, layer=0
2. 雷 → id≥1；根（layer==0）→ id==seed，非根 → id>seed
3. 相邻两雷 → id 相等
4. 非根雷 → 存在邻居 layer == layer-1（且同 id，由 3 保证）

`count[p]`：以 p 为根的分量面积（Σ[id==q]==seed(p)），供面积类规则使用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...ir.expr import (
    And,
    BVar,
    Cmp,
    Iff,
    Imp,
    Lin,
    Not,
    Or,
    sum_of,
)

if TYPE_CHECKING:
    from ...ir.expr import Model
    from ...puzzle.model import Puzzle

_NEIGH4 = ((0, 1), (1, 0), (0, -1), (-1, 0))
_NEIGH8 = _NEIGH4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def build_components(
    model: "Model",
    puzzle: "Puzzle",
    mine_vars: dict[tuple[int, int], int],
    diagonal: bool = False,
) -> dict[tuple[int, int], dict[str, object]]:
    """生成连通分量变量体系，返回 {pos: {"id": Lin, "layer": Lin, "root": BVar, "count": Lin}}。"""
    n = puzzle.width * puzzle.height
    neigh = _NEIGH8 if diagonal else _NEIGH4

    def seed(pos: tuple[int, int]) -> int:
        return pos[0] * puzzle.width + pos[1] + 1  # 1-based

    comps: dict[tuple[int, int], dict[str, object]] = {}
    for r in range(puzzle.height):
        for c in range(puzzle.width):
            pos = (r, c)
            comps[pos] = {
                "id": model.new_int(f"cid_{r}_{c}", 0, n),
                "layer": model.new_int(f"clayer_{r}_{c}", 0, n),
                "root": model.new_bool(f"croot_{r}_{c}"),
                "count": model.new_int(f"ccount_{r}_{c}", 0, n),
            }

    for pos, v in comps.items():
        r, c = pos
        b = BVar(mine_vars[pos])
        id_expr: Lin = v["id"]
        layer_expr: Lin = v["layer"]
        root: object = v["root"]
        s = seed(pos)

        # 1) 非雷 → id=0, layer=0, root=False
        not_b = Not(b)
        model.add(Imp(not_b, Cmp("==", id_expr, Lin((), 0))))
        model.add(Imp(not_b, Cmp("==", layer_expr, Lin((), 0))))
        model.add(Imp(not_b, Not(root)))

        # 2) 雷 → id≥1；根 → id==seed，非根 → id>seed
        model.add(Imp(b, Cmp(">=", id_expr, Lin((), 1))))
        model.add(Iff(root, And((b, Cmp("==", layer_expr, Lin((), 0))))))
        model.add(Imp(And((b, root)), Cmp("==", id_expr, Lin((), s))))
        model.add(Imp(And((b, Not(root))), Cmp(">", id_expr, Lin((), s))))

        # 3) 相邻两雷 → 同 id
        for dr, dc in neigh:
            nr, nc = r + dr, c + dc
            if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width:
                bq = BVar(mine_vars[(nr, nc)])
                model.add(
                    Imp(And((b, bq)), Cmp("==", id_expr, comps[(nr, nc)]["id"]))
                )

        # 4) 非根雷 → 存在邻居 layer == layer-1
        parents = []
        for dr, dc in neigh:
            nr, nc = r + dr, c + dc
            if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width:
                parents.append(
                    Cmp("==", comps[(nr, nc)]["layer"], layer_expr - 1)
                )
        if parents:
            model.add(Imp(And((b, Not(root))), Or(tuple(parents))))

    # 5) 分量面积：count[p] = Σ [id[q] == seed(p)]
    for p, v in comps.items():
        s = seed(p)
        terms = []
        for q, vq in comps.items():
            eq = model.new_bool(f"cid_{p[0]}_{p[1]}_eq_{q[0]}_{q[1]}")
            model.add(Iff(eq, Cmp("==", vq["id"], Lin((), s))))
            terms.append(Lin(((eq.vid, 1),)))
        model.add(Cmp("==", v["count"], sum_of(terms)))

    return comps
