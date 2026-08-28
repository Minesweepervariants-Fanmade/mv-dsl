"""线索求值器：从答案盘计算某格在某规则下的**显示值**。

现在只是组合子管道的薄封装——`ClueRule.value()` 即管道的求值
（Region → Aggregate → Relation），与约束生成（`compiler.py`）语义一致。

用途：
1. **交叉验证**：与官方/legacy 的输出比对，证明规则语义正确
2. **fill**：谜题生成时由答案盘反推线索值
"""

from __future__ import annotations

from typing import Any

from ..registry.rules_mv1 import CLUE_RULES

__all__ = ["clue_value", "get_rule"]


class UnknownRule(ValueError):
    """规则未在注册表中登记。"""


def get_rule(rule: str) -> Any:
    """按规则 id 查注册表（`L+`/`L-` 等带方向后缀的形态）。"""
    try:
        return CLUE_RULES[rule]
    except KeyError:
        raise UnknownRule(f"未知规则: {rule!r}（注册表含 {sorted(CLUE_RULES)}）") from None


def clue_value(puzzle, row: int, col: int, rule: str) -> Any:
    """计算 (row, col) 在 `rule` 下的显示值。

    返回类型依聚合子而定：多数为 int；数墙 [W] 返回段长元组（升序）。
    """
    return get_rule(rule).value(puzzle, row, col)
