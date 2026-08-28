"""线索求值器：从答案盘计算某格在某规则下的**显示值**。

这是规则语义的可执行定义，三个用途：

1. **交叉验证**：与官方/legacy 的输出比对，证明规则语义正确
2. **fill**：谜题生成时由答案盘反推线索值
3. **参照实现**：约束生成器（`compiler.py`）的语义基准——两者必须一致

坐标约定 `cells[row][col]`；邻域顺序沿用官方参考实现
（`D:\\dev\\mv\\legacy\\stat\\puzzle_mv.py`），以保证数墙类规则结果一致。
"""

from __future__ import annotations

from ..puzzle.model import Puzzle

__all__ = ["clue_value", "region", "NEIGH8", "WALL_ORDER", "CROSS2", "CROSS1", "KNIGHT"]

# 8 邻顺序：右 → 右下 → 下 → 左下 → 左 → 左上 → 上 → 右上（顺时针）
NEIGH8: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1),
)
# 数墙从正右方开始顺时针（与官方一致）：右、右下、下、左下、左、左上、上、右上
WALL_ORDER = NEIGH8

# 半径 2 十字（[X] Cross）
CROSS2: tuple[tuple[int, int], ...] = (
    (0, 1), (0, 2), (1, 0), (2, 0), (0, -1), (0, -2), (-1, 0), (-2, 0),
)
# 半径 1 十字（[X'] Mini Cross）
CROSS1: tuple[tuple[int, int], ...] = ((0, 1), (1, 0), (0, -1), (-1, 0))
# 马步（[K] Knight）
KNIGHT: tuple[tuple[int, int], ...] = (
    (1, 2), (2, 1), (1, -2), (2, -1), (-1, 2), (-2, 1), (-1, -2), (-2, -1),
)

_REGIONS: dict[str, tuple[tuple[int, int], ...]] = {
    "moore": NEIGH8,
    "cross2": CROSS2,
    "cross1": CROSS1,
    "knight": KNIGHT,
}


def region(puzzle: Puzzle, row: int, col: int, kind: str) -> list[tuple[int, int]]:
    """返回区域内**在盘内**的格子坐标（越界格自动裁剪）。"""
    deltas = _REGIONS.get(kind)
    if deltas is None:
        raise ValueError(f"未知区域类型: {kind}")
    out = []
    for dr, dc in deltas:
        r, c = row + dr, col + dc
        if 0 <= r < puzzle.height and 0 <= c < puzzle.width:
            out.append((r, c))
    return out


def _is_mine(puzzle: Puzzle, r: int, c: int) -> bool:
    return puzzle.cells[r][c].mine


def _is_colored(puzzle: Puzzle, r: int, c: int) -> bool:
    return puzzle.cells[r][c].colored


def _wall_segments(puzzle: Puzzle, row: int, col: int) -> tuple[int, ...]:
    """数墙：沿 8 邻环形扫描，得到各连续雷段长度（**升序**）。

    官方实现要点：先找一个非雷邻居作为起点；若 8 邻全是雷，则整圈视为一段。
    """
    ring = [(row + dr, col + dc) for dr, dc in WALL_ORDER]
    inside = [
        (r, c) for r, c in ring if 0 <= r < puzzle.height and 0 <= c < puzzle.width
    ]
    if not inside:
        return ()

    start = None
    for idx, (r, c) in enumerate(ring):
        if 0 <= r < puzzle.height and 0 <= c < puzzle.width and not _is_mine(puzzle, r, c):
            start = idx
            break

    segments: list[int] = []
    if start is None:
        # 全为雷：整圈一段
        segments.append(len(inside))
    else:
        ordered = ring[start:] + ring[:start]
        cur = 0
        for r, c in ordered:
            if not (0 <= r < puzzle.height and 0 <= c < puzzle.width):
                # 越界视为断开（官方实现中越界格不贡献但会重置计数）
                if cur > 0:
                    segments.append(cur)
                    cur = 0
                continue
            if _is_mine(puzzle, r, c):
                cur += 1
            elif cur > 0:
                segments.append(cur)
                cur = 0
        if cur > 0:
            segments.append(cur)
    return tuple(sorted(segments))


def _eyesight(puzzle: Puzzle, row: int, col: int) -> tuple[int, int]:
    """纵横视野：各方向连续非雷格数（雷阻挡视线，不含自身）。"""
    vertical = 0
    for r in range(row - 1, -1, -1):
        if not _is_mine(puzzle, r, col):
            vertical += 1
        else:
            break
    for r in range(row + 1, puzzle.height):
        if not _is_mine(puzzle, r, col):
            vertical += 1
        else:
            break
    horizontal = 0
    for c in range(col - 1, -1, -1):
        if not _is_mine(puzzle, row, c):
            horizontal += 1
        else:
            break
    for c in range(col + 1, puzzle.width):
        if not _is_mine(puzzle, row, c):
            horizontal += 1
        else:
            break
    return vertical, horizontal


def _sum(puzzle: Puzzle, cells: list[tuple[int, int]], weight: str) -> int:
    """按权重求和。`weight` ∈ {plain, dye_double, dye_diff, dye_mn}。"""
    total = 0
    for r, c in cells:
        if not _is_mine(puzzle, r, c):
            continue
        colored = _is_colored(puzzle, r, c)
        if weight == "plain":
            total += 1
        elif weight == "dye_double":  # [M] 染色格雷计 2
            total += 2 if colored else 1
        elif weight == "dye_diff":    # [N] 染色 +1、非染色 -1
            total += 1 if colored else -1
        elif weight == "dye_mn":      # [M][N] 染色 +2、非染色 -1
            total += 2 if colored else -1
        else:
            raise ValueError(f"未知权重: {weight}")
    return total


def clue_value(puzzle: Puzzle, row: int, col: int, rule: str) -> int | tuple[int, ...]:
    """计算 (row, col) 在 `rule` 下的显示值。

    `rule` 可带 `+` / `-` 后缀表示误差规则（Liar）方向，如 `L+`、`L-`、`LM+`。
    返回类型：多数规则为 int；数墙 [W] 返回段长元组。
    """
    base = rule.rstrip("+-")
    direction = 0
    if rule.endswith("+"):
        direction = 1
    elif rule.endswith("-"):
        direction = -1

    if base in ("V", "L"):
        # [L] Liar 与 [V] 同区域，差异仅在末尾的 ±1 偏移
        value = _sum(puzzle, region(puzzle, row, col, "moore"), "plain")
    elif base == "M":
        value = _sum(puzzle, region(puzzle, row, col, "moore"), "dye_double")
    elif base == "LM":
        value = _sum(puzzle, region(puzzle, row, col, "moore"), "dye_double")
    elif base == "N":
        value = abs(_sum(puzzle, region(puzzle, row, col, "moore"), "dye_diff"))
    elif base == "MN":
        value = abs(_sum(puzzle, region(puzzle, row, col, "moore"), "dye_mn"))
    elif base == "X":
        value = _sum(puzzle, region(puzzle, row, col, "cross2"), "plain")
    elif base == "MX":
        value = _sum(puzzle, region(puzzle, row, col, "cross2"), "dye_double")
    elif base == "NX":
        value = abs(_sum(puzzle, region(puzzle, row, col, "cross2"), "dye_diff"))
    elif base == "X'":
        value = _sum(puzzle, region(puzzle, row, col, "cross1"), "plain")
    elif base == "K":
        value = _sum(puzzle, region(puzzle, row, col, "knight"), "plain")
    elif base == "W":
        segs = _wall_segments(puzzle, row, col)
        # 官方约定：无雷段时记为 0（对照 legacy 的 `if len(tapas) == 0: return 0`）
        return segs if segs else (0,)
    elif base == "W'":
        segs = _wall_segments(puzzle, row, col)
        return segs[-1] if segs else 0
    elif base == "P":
        return len(_wall_segments(puzzle, row, col))
    elif base == "E":
        v, h = _eyesight(puzzle, row, col)
        return v + h + 1  # 含自身
    elif base == "E'":
        v, h = _eyesight(puzzle, row, col)
        return v - h  # 正=纵向更长(↕)，负=横向更长(↔)，返回带符号差值
    else:
        raise ValueError(f"未知规则: {rule}")

    if direction:
        value = value + direction
        # 官方边界处理：真实值为 0 时无法再 -1，显示为 1 并翻转方向
        # （对照 legacy puzzle_mv.py 中 res == -1 的分支）
        if value < 0:
            value = -value
    return value
