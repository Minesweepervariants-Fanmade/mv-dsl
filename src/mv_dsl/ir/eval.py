"""IR 约束求值：给定变量赋值，检查所有断言是否成立。

用途：把官方答案盘代入，验证「我们的约束」与「官方谜题」语义一致。
相比调用求解器快几个数量级，适合全量关卡回归。
"""

from __future__ import annotations

from dataclasses import dataclass

from .expr import (
    AllDiff,
    AllowedAssignments,
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
    Xor,
)

__all__ = ["Assignment", "evaluate", "check_model", "violations"]


@dataclass(slots=True)
class Assignment:
    """变量赋值：vid → 整数值。"""

    values: dict[int, int]

    def get(self, vid: int) -> int:
        return self.values[vid]


def _lin_value(expr: Lin, a: Assignment) -> int:
    total = expr.const
    for vid, coeff in expr.terms:
        total += coeff * a.values[vid]
    return total


def _cmp(op: str, lhs: int, rhs: int) -> bool:
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    if op == "<=":
        return lhs <= rhs
    if op == "<":
        return lhs < rhs
    if op == ">=":
        return lhs >= rhs
    if op == ">":
        return lhs > rhs
    raise ValueError(f"未知比较符: {op}")


def evaluate(node: object, a: Assignment) -> bool:
    """求值布尔表达式。"""
    if isinstance(node, BConst):
        return node.value
    if isinstance(node, BVar):
        return a.values[node.vid] == 1
    if isinstance(node, Cmp):
        return _cmp(node.op, _lin_value(node.lhs, a), _lin_value(node.rhs, a))
    if isinstance(node, Not):
        return not evaluate(node.x, a)
    if isinstance(node, And):
        return all(evaluate(x, a) for x in node.args)
    if isinstance(node, Or):
        return any(evaluate(x, a) for x in node.args)
    if isinstance(node, Xor):
        return evaluate(node.a, a) != evaluate(node.b, a)
    if isinstance(node, Imp):
        return (not evaluate(node.a, a)) or evaluate(node.b, a)
    if isinstance(node, Iff):
        return evaluate(node.a, a) == evaluate(node.b, a)
    if isinstance(node, AllDiff):
        vals = [_lin_value(e, a) for e in node.args]
        return len(set(vals)) == len(vals)
    if isinstance(node, ModEq):
        return (_lin_value(node.a, a) - _lin_value(node.b, a)) % node.m == 0
    if isinstance(node, AllowedAssignments):
        return tuple(_lin_value(e, a) for e in node.lins) in node.tuples
    raise TypeError(f"不支持的 IR 节点: {type(node).__name__}")


def violations(model: Model, a: Assignment) -> list[int]:
    """返回所有不成立断言的下标。"""
    return [i for i, c in enumerate(model.constraints) if not evaluate(c, a)]


def check_model(model: Model, a: Assignment) -> bool:
    """所有断言是否全部成立。"""
    return not violations(model, a)
