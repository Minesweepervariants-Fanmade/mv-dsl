"""RelationModulo：取模关系（[2M] Modulo）。

线索值与真实值模 3 同余。官方实现用 `sum ∈ {v, v+3, v+6}` 三析举
（mv2 反编译 3539-3553 行），因 8 邻雷数和 ≤ 8，与 `sum ≡ v (mod 3)` 等价；
此处用 IR 的 `ModEq`（CP-SAT 原生 `AddModuloEquality`）更简洁高效。
"""

from __future__ import annotations

from dataclasses import dataclass

from ...ir.expr import ModEq
from .relation import Relation


@dataclass(frozen=True, slots=True)
class RelationModulo(Relation):
    id = "modulo"
    m: int = 3

    def display(self, real_value: int, direction: int = 0) -> int:
        return real_value % self.m

    def apply(self, model, total, clue_var):
        return ModEq(total, self.m, clue_var)
