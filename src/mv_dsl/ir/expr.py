"""后端无关的约束表达式。

设计原则：

- **变量与断言分离**：`Model` = 变量表 + 断言列表，后端各自下译
- **reification 是一等公民**：`Iff(开关变量, 约束)` 表达「条件成立时约束生效」，
  这是规则组合与副板联动的关键（CP-SAT 的 `OnlyEnforceIf`、Z3 的蕴含）
- **线性表达式统一为 `Lin`**：`{vid: coeff} + const`，覆盖绝大多数扫雷约束
  （$\\sum \\text{mine} = n$、`±1` 误差、取模、面积和）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

# 比较运算符
EQ, NE, LE, LT, GE, GT = "==", "!=", "<=", "<", ">=", ">"


@dataclass(frozen=True, slots=True)
class Var:
    """变量声明。`lo=0, hi=1` 即布尔变量。"""

    vid: int
    name: str
    lo: int = 0
    hi: int = 1

    @property
    def is_bool(self) -> bool:
        return self.lo == 0 and self.hi == 1


@dataclass(frozen=True, slots=True)
class Lin:
    """线性表达式 $\\sum c_i x_i + b$。"""

    terms: tuple[tuple[int, int], ...] = ()  # ((vid, coeff), ...)
    const: int = 0

    def __add__(self, other: "Lin | int") -> "Lin":
        if isinstance(other, int):
            return Lin(self.terms, self.const + other)
        return Lin(self.terms + other.terms, self.const + other.const)

    def __radd__(self, other: int) -> "Lin":
        return self.__add__(other)

    def __sub__(self, other: "Lin | int") -> "Lin":
        if isinstance(other, int):
            return Lin(self.terms, self.const - other)
        neg = tuple((vid, -coeff) for vid, coeff in other.terms)
        return Lin(self.terms + neg, self.const - other.const)

    def __mul__(self, k: int) -> "Lin":
        return Lin(tuple((vid, coeff * k) for vid, coeff in self.terms), self.const * k)

    __rmul__ = __mul__


def sum_of(items: Iterable["Lin | int"]) -> Lin:
    """多个线性式求和（布尔变量列表求和即「雷计数」）。"""
    result = Lin()
    for item in items:
        result = result + item
    return result


# ---------------------------------------------------------------- 布尔表达式


@dataclass(frozen=True, slots=True)
class BConst:
    value: bool


@dataclass(frozen=True, slots=True)
class BVar:
    vid: int


@dataclass(frozen=True, slots=True)
class Cmp:
    """线性比较，如 `Lin == 3`。"""

    op: str
    lhs: Lin
    rhs: Lin


@dataclass(frozen=True, slots=True)
class Not:
    x: object


@dataclass(frozen=True, slots=True)
class And:
    args: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Or:
    args: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Xor:
    a: object
    b: object


@dataclass(frozen=True, slots=True)
class Imp:
    """蕴含：$a \\Rightarrow b$"""

    a: object
    b: object


@dataclass(frozen=True, slots=True)
class Iff:
    """等价：$a \\Leftrightarrow b$。用于 reify（条件约束）。"""

    a: object
    b: object


@dataclass(frozen=True, slots=True)
class AllDiff:
    args: tuple[Lin, ...]


@dataclass(frozen=True, slots=True)
class ModEq:
    """同余：$a \\equiv b \\pmod m$（如 [2M] 取模）。"""

    a: Lin
    m: int
    b: Lin


def all_of(args: Iterable[object]) -> object:
    items = tuple(args)
    if not items:
        return BConst(True)
    if len(items) == 1:
        return items[0]
    return And(items)


def any_of(args: Iterable[object]) -> object:
    items = tuple(args)
    if not items:
        return BConst(False)
    if len(items) == 1:
        return items[0]
    return Or(items)


def at_most_one(bools: Iterable[object]) -> object:
    """至多一个为真：两两取反合取（小规模下 CP-SAT 表现良好）。"""
    items = tuple(bools)
    return all_of(
        any_of([Not(items[i]), Not(items[j])])
        for i in range(len(items))
        for j in range(i + 1, len(items))
    )


def exactly_one(bools: Iterable[object]) -> object:
    items = tuple(bools)
    return all_of([any_of(items), at_most_one(items)])


# ---------------------------------------------------------------- 模型


@dataclass(slots=True)
class Model:
    """约束模型：变量表 + 断言列表。"""

    vars: dict[int, Var] = field(default_factory=dict)
    constraints: list[object] = field(default_factory=list)
    _next_vid: int = 0

    def new_bool(self, name: str) -> BVar:
        vid = self._next_vid
        self._next_vid += 1
        self.vars[vid] = Var(vid, name, 0, 1)
        return BVar(vid)

    def new_int(self, name: str, lo: int, hi: int) -> Lin:
        vid = self._next_vid
        self._next_vid += 1
        self.vars[vid] = Var(vid, name, lo, hi)
        return Lin(((vid, 1),))

    def add(self, constraint: object) -> None:
        self.constraints.append(constraint)

    def var_name(self, vid: int) -> str:
        return self.vars[vid].name
