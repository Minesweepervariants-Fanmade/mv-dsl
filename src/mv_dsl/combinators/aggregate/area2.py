"""A2Area：四连通雷区面积之和（[2A] Area）。

语义（对照官方 `ActiveVerticesConnectedArea(list75, i, j, 1+v)`，mv2 反编译 3864-3910 行）：
线索格 (i,j) 相邻的四连通雷区面积之和 == 显示值。等价表述：把 (i,j) 强制视为雷，
其所在四连通雷区面积 == v+1（4 邻各雷区被强制连通成一片）。

实现依赖 compiler 预构建的**连通分量变量体系**（`model.extras["components"]`）：
面积 = Σ_{分量 k 出现在 (i,j) 4 邻} 分量面积。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Iff, Imp, Lin, Not, Or, sum_of
from .aggregate import Aggregate
from ..relation.equals import RelationEquals

_NEIGH4 = ((0, 1), (1, 0), (0, -1), (-1, 0))


class A2Area(Aggregate):
    id = "2area"

    def value(self, puzzle, row, col, cells, weight):
        """从答案盘计算：4 邻雷区的四连通面积之和（去重）。"""
        visited: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = []
        for dr, dc in _NEIGH4:
            nr, nc = row + dr, col + dc
            if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width and puzzle.cells[nr][nc].mine:
                stack.append((nr, nc))
        while stack:
            r, c = stack.pop()
            if (r, c) in visited:
                continue
            visited.add((r, c))
            for dr, dc in _NEIGH4:
                nr, nc = r + dr, c + dc
                if (
                    0 <= nr < puzzle.height
                    and 0 <= nc < puzzle.width
                    and puzzle.cells[nr][nc].mine
                ):
                    stack.append((nr, nc))
        return len(visited)

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("A2Area 仅支持 RelationEquals")
        shown = puzzle.cells[row][col].clue.value
        comps = model.extras["components"]  # 由 compiler 预构建
        n = puzzle.width * puzzle.height

        neighbors = [
            (row + dr, col + dc)
            for dr, dc in _NEIGH4
            if 0 <= row + dr < puzzle.height and 0 <= col + dc < puzzle.width
        ]

        contribs = []
        for pos, v in comps.items():
            seed = pos[0] * puzzle.width + pos[1] + 1
            present = model.new_bool(f"area_p_{seed}")
            model.add(
                Iff(
                    present,
                    Or(
                        tuple(
                            Cmp("==", comps[q]["id"], Lin((), seed)) for q in neighbors
                        )
                    ),
                )
            )
            contrib = model.new_int(f"area_c_{seed}", 0, n)
            model.add(Imp(present, Cmp("==", contrib, v["count"])))
            model.add(Imp(Not(present), Cmp("==", contrib, Lin((), 0))))
            contribs.append(contrib)

        return Cmp("==", sum_of(contribs), Lin((), shown))
