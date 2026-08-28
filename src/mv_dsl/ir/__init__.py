"""L1 约束中间表示：与后端无关。

规则层只产出 `Model`（变量 + 断言），由 `mv_dsl.backends` 下译到具体求解器。
这样换后端（CP-SAT / Z3 / csugar）不需要改动任何规则定义。
"""

from .expr import (
    AllDiff,
    And,
    BConst,
    BVar,
    Cmp,
    Iff,
    Imp,
    Lin,
    Model,
    ModEq,
    Not,
    Or,
    Var,
    Xor,
    all_of,
    any_of,
    at_most_one,
    exactly_one,
    sum_of,
)

__all__ = [
    "AllDiff",
    "And",
    "BConst",
    "BVar",
    "Cmp",
    "Iff",
    "Imp",
    "Lin",
    "Model",
    "ModEq",
    "Not",
    "Or",
    "Var",
    "Xor",
    "all_of",
    "any_of",
    "at_most_one",
    "exactly_one",
    "sum_of",
]
