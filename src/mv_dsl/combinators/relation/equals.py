"""RelationEquals：显示值 == 真实值（绝大多数规则的默认关系）。"""

from __future__ import annotations

from ...ir.expr import Cmp
from .relation import Relation


class RelationEquals(Relation):
    id = "equals"

    def display(self, real_value: int, direction: int = 0) -> int:
        return real_value

    def apply(self, model, total, clue_var):
        return Cmp("==", total, clue_var)
