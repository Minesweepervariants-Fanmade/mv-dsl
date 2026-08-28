"""AEyesight：四方向可见格数（[E] Eyesight）。

值 = 上 + 下 + 左 + 右 的连续可见非雷格数 + 1（含自身）。
雷阻挡视线。约束用**辅助变量链**编码：第 k 格可见 ⟺ 第 k-1 格可见 ∧ 第 k 格非雷，
链在遇雷后全部为假，格数即可见标志之和。
"""

from __future__ import annotations

from ...ir.expr import And, BVar, Iff, Lin, Not, sum_of
from ..relation.relation import Relation
from .aggregate import Aggregate


def vision_chain(
    model, cells: list[tuple[int, int]], mine_vars, tag: str
) -> Lin:
    """某方向连续可见（非雷）格数的表达式。`cells` 必须由近及远排列。"""
    if not cells:
        return Lin()
    terms: list[Lin] = []
    prev = None
    for pos in cells:
        vis = model.new_bool(f"vis_{tag}_{pos[0]}_{pos[1]}")
        not_mine = Not(BVar(mine_vars[pos]))
        model.add(Iff(vis, not_mine if prev is None else And((prev, not_mine))))
        terms.append(Lin(((vis.vid, 1),)))
        prev = vis
    return sum_of(terms)


def _direction_groups(puzzle, row, col, region):
    """从区域的方向分组中取上/下/左/右（REyesight 的 directions 顺序）。"""
    dirs = region.directions(puzzle, row, col)
    if dirs is None:
        raise TypeError("AEyesight 需要支持 directions() 的区域（REyesight）")
    up, down, left, right = dirs
    return up, down, left, right


class AEyesight(Aggregate):
    id = "eyesight"

    def value(self, puzzle, row, col, cells, weight):
        r0, c0 = row, col
        visible = 0
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            r, c = r0 + dr, c0 + dc
            while 0 <= r < puzzle.height and 0 <= c < puzzle.width:
                if puzzle.cells[r][c].mine:
                    break
                visible += 1
                r, c = r + dr, c + dc
        return visible + 1  # 含自身

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        up, down, left, right = _direction_groups(puzzle, row, col, _region_of(puzzle, row, col))
        total = (
            vision_chain(model, up, mine_vars, "u")
            + vision_chain(model, down, mine_vars, "d")
            + vision_chain(model, left, mine_vars, "l")
            + vision_chain(model, right, mine_vars, "r")
            + 1
        )
        return relation.apply(model, total, clue_var, puzzle, row, col)


def _region_of(puzzle, row, col):
    from ..region.eyesight import REyesight

    return REyesight()
