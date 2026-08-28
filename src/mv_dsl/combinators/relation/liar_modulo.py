r"""RelationLiarModulo：误差取模（[2L][2M] Liar+Modulo）——**先取模，再误差**。

官方（mv2 反编译 `GetCellConstraint` case "[2LM]" 4260-4279 行）：
真实雷数 `sum` 先 `mod 3` 得余数 $R$；再按副板 liar 状态决定显示值 $D$：

- 真话（副板对应格非雷）：$D = R$
- 说谎（副板对应格是雷）：$D = R \pm 1$，且 $\pm 1$ **不越界**
  （$R=0$ 只能 $+1$；$R=2$ 只能 $-1$；$R=1$ 双向 $\{0,2\}$）

求解端（显示值 $D$ 已知、liar 状态来自副板）反推真实余数：

- $D \in \{0, 2\}$：liar 格的真实余数**只能是 1**（越界方向被剔除）——游戏教程所述
  「误差值 0 或 2 的真实值只能是 1」
- $D = 1$：liar 格的真实余数 $\in \{0, 2\}$（双向）

约束（与官方 if/else 逐字对应）：

$$D \in \{0,2\}:\quad (\neg liar \Rightarrow R{=}D) \wedge (liar \Rightarrow R{=}1)$$
$$D = 1:\quad \neg liar \Leftrightarrow (R{=}1)$$

liar 状态由 compiler 预构建的误差副板变量（`model.extras["liar_cells"]`，
主格 `(row, col)` → 副板对应格雷布尔变量）提供；显示值 $D$ 是固定值变量
（`clue_var`，`lo == hi == 显示值`）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ...ir.expr import And, Cmp, Iff, Imp, Lin, Not, Or
from .relation import Relation

if TYPE_CHECKING:
    from ...ir.expr import Model
    from ...puzzle.model import Puzzle


@dataclass(frozen=True, slots=True)
class RelationLiarModulo(Relation):
    id = "liar_modulo"
    m: int = 3

    def display(
        self,
        real_value: int,
        direction: int = 0,
        puzzle: "Puzzle | None" = None,
        row: int | None = None,
        col: int | None = None,
    ) -> int:
        if puzzle is None or puzzle.sideboard is None or row is None or col is None:
            raise ValueError("RelationLiarModulo.display 需要 puzzle 与 row/col（读误差副板）")
        r = real_value % self.m
        offset = puzzle.sideboard.width - puzzle.width
        liar = puzzle.sideboard.cells[row][col + offset].lower().startswith("f")
        if not liar:
            return r
        # liar：D = R ± 1（不越界）。方向由谜题数据给定（direction>0 → +1），
        # 无方向时默认 +1；真实值与显示值的关系对求解是双向的（见 apply）。
        return r + 1 if (direction > 0 or r + 1 < self.m) else r - 1

    def apply(
        self,
        model: "Model",
        total: Lin,
        clue_var: Lin,
        puzzle: "Puzzle | None" = None,
        row: int | None = None,
        col: int | None = None,
    ) -> Any:
        # clue_var 是固定值变量（lo == hi == 显示值 D）
        vid = clue_var.terms[0][0]
        d = model.vars[vid].lo
        liar = model.extras["liar_cells"][(row, col)]

        # 枚举展开（官方 `sum == D | sum == D+3 | sum == D+6` / `sum ∈ {1,4,7}`，
        # 因 3×3 雷数和 ≤ 8 与 `sum ≡ D (mod 3)` 等价），可安全嵌入蕴含。
        def same(base: int) -> object:
            return Or(
                tuple(Cmp("==", total, Lin((), base + k * self.m)) for k in range(3))
            )

        ok = same(d)     # R == D（真话）
        other = same(1)  # R == 1（liar，D ∈ {0,2}）
        if d == 0 or d == 2:
            return And((Imp(Not(liar), ok), Imp(liar, other)))
        # d == 1：官方 `~isBomb[liar] == ok`（liar → R ∈ {0,2}）
        return Iff(Not(liar), ok)
