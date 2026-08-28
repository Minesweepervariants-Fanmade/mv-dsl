"""Weight 抽象基类：每颗雷计入多少。

具体子类约定（PROJECT.md §8.2）：命名前缀 `W`，每子类独立文件。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ...puzzle.model import Cell


class Weight(ABC):
    """权重函数：给定格子的染色属性，返回该格是雷时计入的数值。"""

    id: ClassVar[str]

    @abstractmethod
    def coeff(self, cell: "Cell") -> int:
        """雷格计入多少（非雷格记 0，由聚合子处理）。"""
