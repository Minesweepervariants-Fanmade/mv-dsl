"""Constraint（全局谓词）组合子：整盘布局约束（全局规则）。

具体子类约定（PROJECT.md §8.2）：命名前缀 `G`，每子类独立文件。
对照官方 `BuildMetaConstraints`（mv2 反编译）与 `BuildConstraints`（mv1）。

子类前缀 `G` 的命名空间：
- mv1 全局规则：Q(Quad)/T(Triplet)/B(Balance)/U(Unary)/A(AntiKnight)/H(Horizontal)/D(Dual)
- mv2 全局规则：2H/2T/2Z/2F/2C/2G/2S/2B（连通类后续）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ...ir.expr import Model
    from ...puzzle.model import Puzzle


class Constraint(ABC):
    id: ClassVar[str]

    @abstractmethod
    def encode(
        self,
        model: "Model",
        puzzle: "Puzzle",
        mine_vars: dict[tuple[int, int], int],
    ) -> Any:
        """生成整盘布局约束。"""
