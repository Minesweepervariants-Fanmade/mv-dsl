"""mv2 规则注册表：规则 id → ClueRule 管道实例 / Constraint 实例。

mv2 规则 id 均为 `2` 前缀（2X/2D/2P/2M/2A/2X'/2D' 等），与 mv1 互不冲突。

[2E]/[2L] 是**关系层包装**——组合规则 = 基础线索管道（Region∘Weight∘Aggregate）
+ 包装 Relation：
- [2E] 系：`RelationEncrypted`（真实值经副板置换显示为字母 A-H）
- [2L] 系（真实值）：`RelationEquals`；误差值（token 带 `-`，规则 id 后缀 `-`）：
  `RelationOffset`（玩家不知道 +1/-1，真实 ∈ {显示±1}）

新增组合（如 [2ED']）只需在 `_BASE` 加一行——管道自动包装，零额外代码。
"""

from __future__ import annotations

from ..combinators.aggregate import (
    A2Area,
    A2Cross,
    A2CrossEither,
    A2Product,
    AAbsoluteSum,
    AEyesight,
    AGroupCount,
    ASum,
    AWallSegments,
)
from ..combinators.region import (
    RCross,
    REyesight,
    RFull,
    RShiftUp,
    RShiftUpTwo,
    RStd,
)
from ..combinators.relation import (
    RelationEncrypted,
    RelationEquals,
    RelationLiarModulo,
    RelationModulo,
    RelationOffset,
)
from ..combinators.rule import ClueRule
from ..combinators.weight import WIdentity, WDyeDiff, WDyeDouble

# --- mv2 线索规则（非副板类）---
CLUE_RULES: dict[str, ClueRule] = {
    "2X": ClueRule("2X", RStd(), WIdentity(), A2Cross(), RelationEquals()),
    "2X'": ClueRule("2X'", RStd(), WIdentity(), A2CrossEither(), RelationEquals()),
    "2D": ClueRule("2D", RShiftUp(), WIdentity(), ASum(), RelationEquals()),
    "2D'": ClueRule("2D'", RShiftUpTwo(), WIdentity(), ASum(), RelationEquals()),
    "2M": ClueRule("2M", RStd(), WIdentity(), ASum(), RelationModulo(3)),
    "2P": ClueRule("2P", RFull(), WIdentity(), A2Product(), RelationEquals()),
    "2A": ClueRule("2A", RFull(), WIdentity(), A2Area(), RelationEquals()),
}

# --- [2E]/[2L] 组合：基础线索管道 + 关系层包装 ---
# suffix → (Region, Weight, Aggregate)。P 组合用 square 加密（距离积²）。
_BASE: dict[str, tuple] = {
    "":    (RStd,        WIdentity,  ASum),
    "M":   (RStd,        WDyeDouble, ASum),
    "D":   (RShiftUp,    WIdentity,  ASum),
    "X":   (RStd,        WIdentity,  A2Cross),
    "P":   (RFull,       WIdentity,  A2Product),
    "A":   (RFull,       WIdentity,  A2Area),
    "1M":  (RStd,        WDyeDouble, ASum),
    "1N":  (RStd,        WDyeDiff,   AAbsoluteSum),
    "1L":  (RStd,        WIdentity,  ASum),
    "1W":  (RStd,        WIdentity,  AWallSegments),
    "1P":  (RStd,        WIdentity,  AGroupCount),
    "1E":  (REyesight,   WIdentity,  AEyesight),
    "1X":  (RCross,      WIdentity,  ASum),
    "D'":  (RShiftUpTwo, WIdentity,  ASum),
}
for _suffix, (_R, _W, _A) in _BASE.items():
    # [2E] 系：加密（P 组合 square；1L 组合 offset=解密后 ±1）
    _enc = RelationEncrypted(square=(_suffix == "P"), offset=(_suffix == "1L"))
    CLUE_RULES[f"2E{_suffix}"] = ClueRule(f"2E{_suffix}", _R(), _W(), _A(), _enc)
    if _suffix == "M":
        continue  # 2LM/2LM- 语义特殊（先取模再误差，liar 由副板决定），单独注册
    # [2L] 系：真实值（RelationEquals）+ 误差值（RelationOffset，id 后缀 -）
    CLUE_RULES[f"2L{_suffix}"] = ClueRule(f"2L{_suffix}", _R(), _W(), _A(), RelationEquals())
    CLUE_RULES[f"2L{_suffix}-"] = ClueRule(f"2L{_suffix}-", _R(), _W(), _A(), RelationOffset())

# [2L][2M]（Liar+Modulo）：先取模（mod 3）再误差——显示值 D 与真实余数 R 的关系：
# 真话 D==R；说谎 D==R±1（不越界）。误差方向由副板决定（官方 4260-4279 行）。
CLUE_RULES["2LM"] = ClueRule("2LM", RStd(), WIdentity(), ASum(), RelationLiarModulo())
CLUE_RULES["2LM-"] = ClueRule("2LM-", RStd(), WIdentity(), ASum(), RelationLiarModulo())

# --- mv2 全局规则（Constraint 子类）---
# 已实现：2H(横向)/2T(无三连)/2Z(零和)/2F(花田)/2G(面积4)/2G'(面积3)/2S(分段)
#         2C(连方)/2B(桥)/2B'(斜桥)/2S'(分段')
from ..combinators.constraint import (
    C2Bridge,
    C2BridgeDiag,
    C2Connected,
    C2Flower,
    C2Group3,
    C2Group4,
    C2Horizontal,
    C2Segment,
    C2SegmentDiff,
    C2Triplet,
    C2ZeroSum,
)

CONSTRAINTS: dict[str, object] = {
    "2H": C2Horizontal(),
    "2T": C2Triplet(),
    "2Z": C2ZeroSum(),
    "2F": C2Flower(),
    "2G": C2Group4(),
    "2G'": C2Group3(),
    "2S": C2Segment(),
    "2C": C2Connected(),
    "2B": C2Bridge(),
    "2B'": C2BridgeDiag(),
    "2S'": C2SegmentDiff(),
}
