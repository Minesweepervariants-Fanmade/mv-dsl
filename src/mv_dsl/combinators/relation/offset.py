"""RelationOffset：误差关系，显示值 == 真实值 ± 1（[L]/[LM] Liar 家族）。

官方约束实现（对照 mv2 反编译 `GetCellConstraint` 3517-3537 行）：
`sum == n+1 ∨ sum == n-1`——**不依赖方向后缀**，真实值非负自动覆盖
「显示值为负时翻转方向」的边界情形（真实 0、方向 -1 时显示 1）。

`display()` 的边界处理与官方一致：真实值 + 方向为负时取反。
"""

from __future__ import annotations

from dataclasses import dataclass

from ...ir.expr import Cmp, Lin, Or
from .relation import Relation


@dataclass(frozen=True, slots=True)
class RelationOffset(Relation):
    id = "offset"
    direction: int = 1  # +1（[L+]/[LM+]）或 -1（[L-]/[LM-]），仅影响显示值计算

    def display(self, real_value: int) -> int:
        shown = real_value + self.direction
        return -shown if shown < 0 else shown  # 官方边界：为负时翻转

    def apply(self, model, total: Lin, clue_var: Lin):
        # 真实值 == 显示值 ± 1（方向无关）
        return Or(
            (
                Cmp("==", total, Lin(((clue_var.terms[0][0], 1),), -1)),
                Cmp("==", total, Lin(((clue_var.terms[0][0], 1),), 1)),
            )
        )
