"""Relation 抽象基类：真实值 ↔ 显示值的变换。

具体子类约定（PROJECT.md §8.2）：命名前缀 `Relation`（避免与 Region 的 `R` 冲突），
每子类独立文件。

- `display(real_value, direction=0, puzzle=None)`：真实值 → 显示值（fill / evaluator 用）。
  `direction` 是**谜题数据**层面的信息（如 [L+] / [L-] 的符号），不是玩家知识——
  玩家只看到显示值，求解时由 `apply` 的双向约束推断真实值。
  `puzzle` 供需要谜题上下文的关系使用（如 [2E] 加密置换表）。
- `apply(model, total, clue_var, puzzle=None)`：真实值表达式 → 线索值的约束（compiler 用）。
  `model.extras` 可携带编译器预构建的共享变量（如 [2E] 的副板置换列）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...ir.expr import Lin, Model
    from ...puzzle.model import Puzzle


class Relation(ABC):
    id: ClassVar[str]

    @abstractmethod
    def display(
        self,
        real_value: int,
        direction: int = 0,
        puzzle: "Puzzle | None" = None,
        row: int | None = None,
        col: int | None = None,
    ) -> int:
        """真实值 → 显示值。`direction` 仅误差类规则使用（谜题数据的方向）；
        `row`/`col` 供需要按格读谜题上下文的关系使用（如 [2L] 系读误差副板）。"""

    @abstractmethod
    def apply(
        self,
        model: "Model",
        total: "Lin",
        clue_var: "Lin",
        puzzle: "Puzzle | None" = None,
        row: int | None = None,
        col: int | None = None,
    ) -> Any:
        """生成「真实值表达式 ↔ 线索值」的约束。"""
