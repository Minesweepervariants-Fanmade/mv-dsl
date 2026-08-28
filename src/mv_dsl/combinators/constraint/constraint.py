"""Constraint（全局谓词）组合子：整盘布局约束（全局规则）。

具体子类约定（PROJECT.md §8.2）：命名前缀 `G`，每子类独立文件。
（mv1 的 1Q/1C/1T/1O/1D/1S/1B 等全局规则将以此为基类实现。）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...ir.expr import Model


class Constraint(ABC):
    id: ClassVar[str]

    @abstractmethod
    def encode(self, model: "Model", mine_vars: dict[tuple[int, int], int]) -> Any:
        """生成整盘布局约束。"""
