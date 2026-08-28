"""Region 抽象基类：区域函数 $(i,j) \\to$ 格子集合。

具体子类约定（PROJECT.md §8.2）：命名前缀 `R`，每子类独立文件。

方向常量沿用官方参考实现（`legacy/stat/puzzle_mv.py`）的邻域顺序，
保证数墙类规则结果一致（环形扫描依赖顺序）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ...puzzle.model import Puzzle


# 8 邻顺序：右 → 右下 → 下 → 左下 → 左 → 左上 → 上 → 右上（顺时针）
NEIGH8: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1),
)
# 数墙从正右方开始顺时针（与官方一致）
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


class Region(ABC):
    """区域函数。`cells()` 返回盘内格子（越界自动裁剪）。"""

    id: ClassVar[str]

    @abstractmethod
    def cells(self, puzzle: "Puzzle", row: int, col: int) -> list[tuple[int, int]]:
        """区域内所有**在盘内**的格子坐标。"""

    def directions(
        self, puzzle: "Puzzle", row: int, col: int
    ) -> list[list[tuple[int, int]]] | None:
        """按方向分组返回格子（如视线四向）。默认无——多数区域无需方向语义。"""
        return None
