"""mv1 规则注册表：规则 id → ClueRule 管道实例。

**新增规则 = 新增子类（如需）+ 在此加一行；组合规则零额外代码。**
注意 id 是**导入器输出的形态**：误差规则带方向后缀（`L+`/`L-`/`LM+`/`LM-`），
与官方 board 字母的 G/L 编码一一对应（见 `puzzle/importer_mv1.py` 的 `CLUE_LETTERS`）。
"""

from __future__ import annotations

from ..combinators.aggregate import (
    AAbsoluteSum,
    AEyesight,
    AGroupCount,
    ALongestWall,
    ASightDiff,
    ASum,
    AWallSegments,
)
from ..combinators.region import (
    REyesight,
    RKnight,
    RMiniCross,
    RStd,
    RCross,
)
from ..combinators.relation import RelationEquals, RelationOffset
from ..combinators.rule import ClueRule
from ..combinators.weight import (
    WDyeDiff,
    WDyeDouble,
    WDyeMn,
    WIdentity,
)

# 规则 id → 管道实例（Region ∘ Weight ∘ Aggregate ∘ Relation）
CLUE_RULES: dict[str, ClueRule] = {
    # --- 线性求和类 ---
    "V": ClueRule("V", RStd(), WIdentity(), ASum(), RelationEquals()),
    "L+": ClueRule("L+", RStd(), WIdentity(), ASum(), RelationOffset()),
    "L-": ClueRule("L-", RStd(), WIdentity(), ASum(), RelationOffset()),
    "M": ClueRule("M", RStd(), WDyeDouble(), ASum(), RelationEquals()),
    "LM+": ClueRule("LM+", RStd(), WDyeDouble(), ASum(), RelationOffset()),
    "LM-": ClueRule("LM-", RStd(), WDyeDouble(), ASum(), RelationOffset()),
    "X": ClueRule("X", RCross(), WIdentity(), ASum(), RelationEquals()),
    "X'": ClueRule("X'", RMiniCross(), WIdentity(), ASum(), RelationEquals()),
    "MX": ClueRule("MX", RCross(), WDyeDouble(), ASum(), RelationEquals()),
    "K": ClueRule("K", RKnight(), WIdentity(), ASum(), RelationEquals()),
    # --- 绝对值类（Negative 家族）---
    "N": ClueRule("N", RStd(), WDyeDiff(), AAbsoluteSum(), RelationEquals()),
    "NX": ClueRule("NX", RCross(), WDyeDiff(), AAbsoluteSum(), RelationEquals()),
    "MN": ClueRule("MN", RStd(), WDyeMn(), AAbsoluteSum(), RelationEquals()),
    # --- 数墙类（表约束）---
    "W": ClueRule("W", RStd(), WIdentity(), AWallSegments(), RelationEquals()),
    "W'": ClueRule("W'", RStd(), WIdentity(), ALongestWall(), RelationEquals()),
    "P": ClueRule("P", RStd(), WIdentity(), AGroupCount(), RelationEquals()),
    # --- 视野类（辅助变量链）---
    "E": ClueRule("E", REyesight(), WIdentity(), AEyesight(), RelationEquals()),
    "E'": ClueRule("E'", REyesight(), WIdentity(), ASightDiff(), RelationEquals()),
}

# --- mv1 全局规则（Constraint 子类）---
# 已实现：Q(Quad)/T(Triplet)/B(Balance)/D(Dual)/U(Unary)/A(AntiKnight)/H(Horizontal)
#         C(八连通)/T'(必三连)/O(Outside)/S(Snake)/D'(Battleship)
from ..combinators.constraint import (
    CAntiKnight,
    CBalance,
    CBattleship,
    CConnected,
    COutside,
    CSnake,
    CDual,
    CHorizontal,
    CQuad,
    CTriplet,
    CTripletReq,
    CUnary,
)

CONSTRAINTS: dict[str, object] = {
    "Q": CQuad(),
    "T": CTriplet(),
    "B": CBalance(),
    "D": CDual(),
    "U": CUnary(),
    "A": CAntiKnight(),
    "H": CHorizontal(),
    "C": CConnected(),
    "T'": CTripletReq(),
    "O": COutside(),
    "S": CSnake(),
    "D'": CBattleship(),
}
