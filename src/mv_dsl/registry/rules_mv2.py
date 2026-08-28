"""mv2 规则注册表：规则 id → ClueRule 管道实例 / Constraint 实例。

本文件先登记**非副板类**规则（副板规则 2E/2L/2E^/2L'/2E'/2I/2U 后续实现）。
注意 mv2 的规则 id 均为 `2` 前缀（2X/2D/2P/2M/2A/2X'/2D' 等），
与 mv1 的单字母/1 前缀规则（V/M/L/...）互不冲突。
"""

from __future__ import annotations

from ..combinators.aggregate import (
    A2Area,
    A2Cross,
    A2CrossEither,
    A2Product,
    ASum,
)
from ..combinators.region import (
    RFull,
    RStd,
    RShiftUp,
    RShiftUpTwo,
)
from ..combinators.relation import RelationEquals, RelationModulo
from ..combinators.rule import ClueRule
from ..combinators.weight import WIdentity

# --- mv2 线索规则（非副板类）---
CLUE_RULES: dict[str, ClueRule] = {
    "2X": ClueRule("2X", RStd(), WIdentity(), A2Cross(), RelationEquals()),
    "2X'": ClueRule("2X'", RStd(), WIdentity(), A2CrossEither(), RelationEquals()),
    "2D": ClueRule("2D", RShiftUp(), WIdentity(), ASum(), RelationEquals()),
    "2D'": ClueRule("2D'", RShiftUpTwo(), WIdentity(), ASum(), RelationEquals()),
    "2M": ClueRule("2M", RStd(), WIdentity(), ASum(), RelationModulo(3)),
    "2P": ClueRule("2P", RFull(), WIdentity(), A2Product(), RelationEquals()),
    "2A": ClueRule("2A", RFull(), WIdentity(), A2Area(), RelationEquals()),
    # 副板类规则（2E/2L/2E^/2L'/2E'/2I/2U）后续实现
}

# --- mv2 全局规则（Constraint 子类）---
# 已实现：2H(横向)/2T(无三连)/2Z(零和)/2F(花田)
# 未实现（连通类）：2C(连方矩形)/2G(面积4)/2G'(面积3)/2S(分段)/2B(桥)
from ..combinators.constraint import C2Group4, C2Group3, C2Horizontal, C2Segment, C2Triplet, C2ZeroSum, C2Flower

CONSTRAINTS: dict[str, object] = {
    "2H": C2Horizontal(),
    "2T": C2Triplet(),
    "2Z": C2ZeroSum(),
    "2F": C2Flower(),
    "2G": C2Group4(),
    "2G'": C2Group3(),
    "2S": C2Segment(),
}
