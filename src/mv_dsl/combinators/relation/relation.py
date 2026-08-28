"""Relation 抽象基类：真实值 ↔ 显示值的变换。

具体子类约定（PROJECT.md §8.2）：命名前缀 `Relation`（避免与 Region 的 `R` 冲突），
每子类独立文件。

- `display(real_value)`：真实值 → 显示值（fill / evaluator 用）
- `apply(model, total, clue_var)`：真实值表达式 → 线索值的约束（compiler 用）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...ir.expr import Lin, Model


class Relation(ABC):
    id: ClassVar[str]

    @abstractmethod
    def display(self, real_value: int) -> int:
        """真实值 → 显示值。"""

    @abstractmethod
    def apply(self, model: "Model", total: "Lin", clue_var: "Lin") -> Any:
        """生成「真实值表达式 ↔ 线索值」的约束。"""
