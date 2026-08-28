"""RelationOffset：误差关系（[L]/[LM] Liar 家族）——显示值 = 真实值 ± 1，**方向未知**。

**语义（玩家视角）**：谜题文件知道误差方向（mv1 规则 id `[L+]`/`[L-]`、mv2 token
带符号如 `2l-4`），但**玩家不知道**——只看到显示值，需要推断真实值 ∈ {显示−1, 显示+1}
哪个可能。因此：

- `display(real, direction)`：**出题端**（fill / 验证）由谜题数据的方向计算显示值
  （真实值 + 方向，为负时翻转——官方边界：真实 0、方向 −1 时显示 1）
- `apply(...)`：**求解端**（玩家视角）双向析取 `sum == clue−1 ∨ sum == clue+1`，
  不依赖方向（对照 mv2 反编译 `GetCellConstraint` 3517-3537 行）

`direction` 不是本组合子的字段——它是谜题实例的属性，由求值端从规则 id / token
符号解析后传入 `display`。
"""

from __future__ import annotations

from dataclasses import dataclass

from ...ir.expr import Cmp, Lin, Or
from .relation import Relation


@dataclass(frozen=True, slots=True)
class RelationOffset(Relation):
    id = "offset"

    def display(self, real_value: int, direction: int = 0, puzzle=None, row=None, col=None) -> int:
        shown = real_value + direction
        return -shown if shown < 0 else shown  # 官方边界：为负时翻转

    def apply(self, model, total: Lin, clue_var: Lin, puzzle=None, row=None, col=None):
        # 真实值 == 显示值 ± 1（玩家视角，方向无关）
        return Or(
            (
                Cmp("==", total, Lin(((clue_var.terms[0][0], 1),), -1)),
                Cmp("==", total, Lin(((clue_var.terms[0][0], 1),), 1)),
            )
        )
