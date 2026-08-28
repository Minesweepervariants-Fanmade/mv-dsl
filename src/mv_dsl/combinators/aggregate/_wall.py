"""数墙类聚合的**官方风格**编码（对照 14mv1 反编译 `MinesweeperSolver.cs`）。

三个关键事实（均经程序验证 / 源码对照）：

1. **[P] 段数 = 段起点计数**：官方用 `CountTrue(b[d] ∧ ¬b[d-1])`（1169-1214 行）——
   环形扫描中每个连续雷段的**首格**。纯线性约束，比表约束高效。
   越界格视为非雷（前一个方向越界时 `b[d]` 直接算起点）；
   8 邻全在盘内且全雷时整圈为一段（官方追加 `FoldAnd(mines)` 特例）。

2. **[W'] 最长段 = 布尔组合**：最长段 ≤ w ⟺ 无 (w+1) 连续雷 ⟺ 每个
   (w+1)-窗口至少一个非雷（合取）；最长段 ≥ w ⟺ 存在 w 连续雷段（析取）。
   官方用 `TapaLargestNumberMapping` 布局析取，此处用窗口布尔组合，无表约束。

3. **[W] 数墙 ↔ (V, P, W') 一一对应**（程序验证：23 种段长串 ↔ 23 种三元组，单射）：
   故 1W 的约束可分解为「雷数 == V」∧「段起点计数 == P」∧「最长段 == W'」
   三个约束的合取——官方尚未采用此优化。
"""

from __future__ import annotations

from ...ir.expr import (
    And,
    BConst,
    BVar,
    Cmp,
    Iff,
    Lin,
    Not,
    all_of,
    any_of,
    sum_of,
)
from ..region.region import WALL_ORDER

__all__ = ["group_count_lin", "longest_wall_bool", "ring_mine_count"]


def _ring(puzzle, row: int, col: int) -> list[tuple[int, int] | None]:
    """8 邻（按 WALL_ORDER），越界格记为 None。"""
    out = []
    for dr, dc in WALL_ORDER:
        r, c = row + dr, col + dc
        out.append((r, c) if 0 <= r < puzzle.height and 0 <= c < puzzle.width else None)
    return out


def ring_mine_count(
    puzzle, row: int, col: int, mine_vars: dict[tuple[int, int], int]
) -> Lin:
    """8 邻雷数的线性表达式（[W] 分解中的 V 约束）。"""
    terms = []
    for pos in _ring(puzzle, row, col):
        if pos is not None:
            terms.append(Lin(((mine_vars[pos], 1),)))
    return sum_of(terms)


def group_count_lin(
    model, puzzle, row: int, col: int, mine_vars: dict[tuple[int, int], int]
) -> Lin:
    """段起点计数的线性表达式（官方 [P] 的 `CountTrue(b ∧ ¬b_prev)`）。"""
    ring = _ring(puzzle, row, col)
    starts: list[Lin] = []

    for d, pos in enumerate(ring):
        if pos is None:
            continue  # 当前方向越界：不参与计数
        prev = ring[(d - 1) % 8]
        if prev is None:
            expr = BVar(mine_vars[pos])  # 前一个方向越界 → ¬b_prev 恒真
        else:
            expr = And((BVar(mine_vars[pos]), Not(BVar(mine_vars[prev]))))
        aux = model.new_bool(f"segstart_{row}_{col}_{d}")
        model.add(Iff(aux, expr))
        starts.append(Lin(((aux.vid, 1),)))

    # 全雷特例：8 邻全部在盘内且全雷 → 整圈一段（官方追加 FoldAnd(mines)）
    if all(p is not None for p in ring):
        aux = model.new_bool(f"segstart_all_{row}_{col}")
        model.add(Iff(aux, all_of(BVar(mine_vars[p]) for p in ring if p is not None)))
        starts.append(Lin(((aux.vid, 1),)))

    return sum_of(starts)


def longest_wall_bool(
    model, puzzle, row: int, col: int, w: int, mine_vars: dict[tuple[int, int], int]
):
    """「最长段 == w」的布尔约束：无 (w+1) 连续雷 ∧ 存在 w 连续雷。"""
    ring = _ring(puzzle, row, col)
    n = len(ring)

    def window(s: int, k: int) -> list[tuple[int, int] | None]:
        return [ring[(s + i) % n] for i in range(k)]

    # 上限：每个 (w+1)-窗口至少一个非雷（越界即非雷）
    upper: list[object] = []
    if w + 1 <= n:
        for s in range(n):
            upper.append(
                any_of(
                    Not(BVar(mine_vars[pos]))
                    if pos is not None
                    else BConst(True)
                    for pos in window(s, w + 1)
                )
            )

    # 下限：存在 w 连续雷窗口（窗口必须全部在盘内；越界窗口不可能全雷，跳过）
    if w == 0:
        lower: list[object] = [BConst(True)]  # 最长段 ≥ 0 恒真
    else:
        lower = [
            all_of(BVar(mine_vars[pos]) for pos in window(s, w) if pos is not None)
            for s in range(n)
            if all(pos is not None for pos in window(s, w))
        ]

    return And((all_of(upper), any_of(lower)))


def decode_segments(encoded: int) -> tuple[int, ...]:
    """显示值（十进制拼接，如 123）→ 段长元组 (1,2,3)。`0` → 空段。"""
    if encoded <= 0:
        return ()
    return tuple(int(ch) for ch in str(encoded))
