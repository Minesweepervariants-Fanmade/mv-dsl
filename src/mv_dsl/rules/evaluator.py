"""线索求值器：从答案盘计算某格在某规则下的**显示值**。

现在只是组合子管道的薄封装——`ClueRule.value()` 即管道的求值
（Region → Aggregate → Relation），与约束生成（`compiler.py`）语义一致。

用途：
1. **交叉验证**：与官方/legacy 的输出比对，证明规则语义正确
2. **fill**：谜题生成时由答案盘反推线索值
"""

from __future__ import annotations

from typing import Any

from ..registry.rules_mv1 import CLUE_RULES as _MV1
from ..registry.rules_mv2 import CLUE_RULES as _MV2

# 合并两代注册表（id 无冲突：mv1 单字母/1 前缀，mv2 2 前缀）
CLUE_RULES: dict[str, object] = {**_MV1, **_MV2}

# mv2 关卡中的 1 代线索规则使用带 `1` 前缀的 token（如 `1p2` → 规则 "1P"），
# 与 mv1 的字母编码（"P"）是同一规则 → 别名映射。
# 1L 无方向后缀（官方 ±1 双向约束，方向仅影响显示），映射到 L+（约束一致）。
_ALIASES: dict[str, str] = {
    "1P": "P",
    "1W": "W",
    "1W'": "W'",
    "1X": "X",
    "1X'": "X'",
    "1E": "E",
    "1E'": "E'",
    "1M": "M",
    "1N": "N",
    "1K": "K",
    "1L": "L+",
}

__all__ = ["clue_value", "get_rule", "CLUE_RULES"]


class UnknownRule(ValueError):
    """规则未在注册表中登记。"""


def get_rule(rule: str) -> Any:
    """按规则 id 查注册表（支持 `L+`/`L-` 方向后缀与 `1` 前缀别名）。"""
    if rule in CLUE_RULES:
        return CLUE_RULES[rule]
    alias = _ALIASES.get(rule)
    if alias is not None:
        return CLUE_RULES[alias]
    raise UnknownRule(
        f"未知规则: {rule!r}（注册表含 {sorted(CLUE_RULES)}，别名含 {sorted(_ALIASES)}）"
    ) from None


def clue_value(puzzle, row: int, col: int, rule: str) -> Any:
    """计算 (row, col) 在 `rule` 下的显示值。

    返回类型依聚合子而定：多数为 int；数墙 [W] 返回段长元组（升序）。
    """
    return get_rule(rule).value(puzzle, row, col)
