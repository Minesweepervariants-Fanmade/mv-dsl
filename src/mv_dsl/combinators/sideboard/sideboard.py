"""Sideboard（副板）组合子：额外未知变量 + 副板布局（副板规则）。

具体子类约定（PROJECT.md §8.2）：命名前缀 `S`，每子类独立文件。
（mv2 的 2E 置换矩阵 / 2L 误差标记 / 2I 方向掩码 / 2U 列计数以此为基类实现。）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...ir.expr import Model
    from ...puzzle.model import Puzzle


class Sideboard(ABC):
    id: ClassVar[str]

    @abstractmethod
    def encode(
        self, model: "Model", puzzle: "Puzzle", mine_vars: dict[tuple[int, int], int]
    ) -> Any:
        """声明副板变量并生成副板相关约束。"""
