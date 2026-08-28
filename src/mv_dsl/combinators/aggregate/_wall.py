"""数墙类聚合共用：邻域 → 段长的表约束生成。"""

from __future__ import annotations

from ...ir.expr import AllowedAssignments, Lin
from ...puzzle.model import Puzzle
from ..region.region import WALL_ORDER
from .aggregate import wall_segments_from


def wall_table(
    puzzle: Puzzle, row: int, col: int, rule: str
) -> tuple[list[tuple[int, int]], tuple[tuple[int, ...], ...]]:
    """枚举 8 邻全部雷布局，生成 (布局, 取值) 表。

    `rule` ∈ {"W", "W'", "P"}，决定取值形态：
    - W  数墙：段长升序拼接为十进制（段长 1-8 单数字，拼接无歧义）
    - W' 最长段
    - P  段数
    越界格视为非雷（官方环形扫描中越界只切段不计数）。
    """
    ring = [(row + dr, col + dc) for dr, dc in WALL_ORDER]
    inside_idx = [
        i
        for i, (r, c) in enumerate(ring)
        if 0 <= r < puzzle.height and 0 <= c < puzzle.width
    ]
    neighbors = [ring[i] for i in inside_idx]

    tuples = []
    for mask in range(1 << len(neighbors)):
        layout = [bool(mask >> k & 1) for k in range(len(neighbors))]
        full: list[bool] = [False] * 8
        for slot, (r, c) in zip(inside_idx, neighbors):
            full[slot] = layout[neighbors.index((r, c))]
        segments = wall_segments_from(tuple(full))
        if rule == "W":
            value = int("".join(str(s) for s in segments)) if segments else 0
        elif rule == "W'":
            value = segments[-1] if segments else 0
        else:  # P
            value = len(segments)
        tuples.append(tuple([1 if b else 0 for b in layout] + [value]))
    return neighbors, tuple(tuples)


def encode_wall_table(
    model, puzzle, row, col, rule, mine_vars, clue_var,
):
    """生成表约束：邻域雷布局 ↔ 编码值。"""
    neighbors, table = wall_table(puzzle, row, col, rule)
    lins = [Lin(((mine_vars[pos], 1),)) for pos in neighbors]
    lins.append(Lin(((clue_var.terms[0][0], 1),)))
    return AllowedAssignments(tuple(lins), table)
