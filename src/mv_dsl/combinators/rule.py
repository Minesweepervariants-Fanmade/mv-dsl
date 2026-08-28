"""ClueRule：线索规则的**管道**——Region ∘ Weight ∘ Aggregate ∘ Relation 的组合。

```python
V = ClueRule("V", RStd(), WIdentity(), ASum(), RelationEquals())
```

- `value(puzzle, r, c, direction=0)`：从答案盘计算显示值（fill / 验证）；
  `direction` 是谜题数据层面的误差方向（L+/L-），仅误差类关系使用
- `encode(model, puzzle, r, c, mine_vars, clue_var)`：生成约束（玩家视角，不含方向）

求值器与编译器都只依赖这两个方法，保证语义一致。
**组合规则零额外代码**——新的组合只是换用不同的子类实例。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .aggregate.aggregate import Aggregate
    from .region.region import Region
    from .relation.relation import Relation
    from .weight.weight import Weight


@dataclass(frozen=True, slots=True)
class ClueRule:
    rule_id: str
    region: "Region"
    weight: "Weight"
    aggregate: "Aggregate"
    relation: "Relation"

    def value(self, puzzle, row: int, col: int, direction: int = 0) -> Any:
        cells = self.region.cells(puzzle, row, col)
        real = self.aggregate.value(puzzle, row, col, cells, self.weight)
        return self.relation.display(real, direction, puzzle, row, col)

    def encode(self, model, puzzle, row: int, col: int, mine_vars, clue_var) -> Any:
        cells = self.region.cells(puzzle, row, col)
        return self.aggregate.encode(
            model, puzzle, row, col, cells, self.weight, mine_vars, clue_var, self.relation
        )

    def __repr__(self) -> str:
        return (
            f"ClueRule({self.rule_id}: "
            f"{self.region.id}∘{self.weight.id}∘{self.aggregate.id}∘{self.relation.id})"
        )
