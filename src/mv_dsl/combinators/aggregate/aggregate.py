"""Aggregate 抽象基类：格子集合 → 数值。

具体子类约定（PROJECT.md §8.2）：命名前缀 `A`，每子类独立文件。

每个聚合子必须实现两个方法（求值器与编译器共用，保证语义一致）：

- `value(puzzle, cells, weight)`：从答案盘计算**真实值**（Relation 应用前）
- `encode(model, puzzle, cells, weight, mine_vars, clue_var, relation)`：
  生成「真实值表达式 ↔ 线索值」的约束，relation 负责最终的偏移/等价变换

两种编码形态：
- 线性类（`ASum`）：真实值为加权和，直接线性约束
- 结构类（数墙、视野）：真实值不是邻域线性和，用表约束 / 辅助变量链
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...ir.expr import Lin, Model
    from ...puzzle.model import Puzzle
    from ..relation.relation import Relation
    from ..weight.weight import Weight


def wall_segments_from(mines: tuple[bool, ...]) -> tuple[int, ...]:
    """数墙纯函数：给定 8 邻雷布局（**越界格记为 False**），返回升序段长。

    环形段的集合与起点选择无关，故从任意断点（非雷/越界）起扫结果一致。
    官方约定：无雷段时记为 `(0,)`。
    """
    if not mines:
        return ()
    if all(mines):
        return (len(mines),)

    start = mines.index(False)
    ordered = mines[start:] + mines[:start]
    segments: list[int] = []
    cur = 0
    for is_mine in ordered:
        if is_mine:
            cur += 1
        elif cur > 0:
            segments.append(cur)
            cur = 0
    if cur > 0:
        segments.append(cur)
    return tuple(sorted(segments))


class Aggregate(ABC):
    id: ClassVar[str]

    @abstractmethod
    def value(
        self, puzzle: "Puzzle", row: int, col: int,
        cells: list[tuple[int, int]], weight: "Weight",
    ):
        """从答案盘计算真实值。"""

    @abstractmethod
    def encode(
        self,
        model: "Model",
        puzzle: "Puzzle",
        row: int,
        col: int,
        cells: list[tuple[int, int]],
        weight: "Weight",
        mine_vars: dict[tuple[int, int], int],
        clue_var: "Lin",
        relation: "Relation",
    ) -> Any:
        """生成约束：真实值表达式 ↔ 线索值（经 relation）。"""
