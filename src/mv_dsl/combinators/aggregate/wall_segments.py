"""AWallSegments：数墙段长序列（[W] Wall）。

**优化**（用户提议，程序已验证）：(V, 1P, 1W') 三元组 ↔ 1W 段长串**一一对应**
（枚举 256 种布局，23 种段长串 ↔ 23 种三元组，单射）。

故 1W 的约束分解为三个更高效的约束之合取，**无表约束**：

$$\\text{1W}(s) \\iff \\underbrace{\\Sigma \\text{mine} = V}_{\\text{线性}} \\land
\\underbrace{\\text{段起点计数} = P}_{\\text{线性（官方 [P] 风格）}} \\land
\\underbrace{\\text{最长段} = W'}_{\\text{窗口布尔组合}}$$

`value()` 仍返回段长元组（显示/验证用）；`encode()` 从显示值解析出 (V, P, W')。
"""

from __future__ import annotations

from ...ir.expr import And, Cmp, Lin
from ..region.region import WALL_ORDER
from ._wall import decode_segments, group_count_lin, longest_wall_bool, ring_mine_count
from .aggregate import Aggregate, wall_segments_from
from ..relation.equals import RelationEquals


class AWallSegments(Aggregate):
    id = "wall_segments"

    def value(self, puzzle, row, col, cells, weight):
        mines = tuple(
            0 <= r < puzzle.height
            and 0 <= c < puzzle.width
            and puzzle.cells[r][c].mine
            for r, c in [(row + dr, col + dc) for dr, dc in WALL_ORDER]
        )
        segments = wall_segments_from(mines)
        return segments if segments else (0,)

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        if not isinstance(relation, RelationEquals):
            raise NotImplementedError("AWallSegments 仅支持 RelationEquals")

        # 显示值（段长串的十进制拼接，如 123）→ 段长 → (V, P, W')
        segments = decode_segments(puzzle.cells[row][col].clue.value)
        v = sum(segments)
        p = len(segments)
        w = segments[-1] if segments else 0

        # 三个约束的合取：(V) ∧ (P 段起点计数) ∧ (W' 最长段)
        return And(
            (
                Cmp("==", ring_mine_count(puzzle, row, col, mine_vars), Lin((), v)),
                Cmp("==", group_count_lin(model, puzzle, row, col, mine_vars), Lin((), p)),
                longest_wall_bool(model, puzzle, row, col, w, mine_vars),
            )
        )
