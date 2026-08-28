"""CP-SAT 后端（主后端）。

把后端无关的 `Model` 下译到 OR-Tools CP-SAT。

选型理由（详见 PROJECT.md §7）：本项目的约束形态是「每格一个布尔 + 大量
$\\sum \\text{bool} = n$ + reify + 少量全局结构」，正是 CP-SAT 的原生最优场景：
伪布尔/线性传播、LP 松弛、多 worker 并行、强 presolve。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ortools.sat.python import cp_model

from ..ir.expr import (
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
    Var,
    Xor,
)

__all__ = ["SolveResult", "SolverConfig", "solve", "solve_all", "compile_model"]


@dataclass(slots=True)
class SolverConfig:
    """求解参数。默认值沿用 fanmade 项目实证有效的配置思路。"""

    num_workers: int = 8
    max_time_seconds: float = 0.0  # 0 表示不限时
    random_seed: int = 42
    linearization_level: int = 2
    randomize_search: bool = True


@dataclass(slots=True)
class SolveResult:
    status: str  # OPTIMAL / FEASIBLE / INFEASIBLE / UNKNOWN / MODEL_INVALID
    values: dict[int, int] = field(default_factory=dict)  # vid → 值
    wall_time: float = 0.0

    @property
    def satisfiable(self) -> bool:
        return self.status in ("OPTIMAL", "FEASIBLE")


def compile_model(
    model: Model, target: cp_model.CpModel | None = None
) -> tuple[cp_model.CpModel, dict[int, Any]]:
    """把 IR 模型下译为 CP-SAT 模型，返回 (CpModel, vid→CP-SAT 变量)。"""
    out = target if target is not None else cp_model.CpModel()
    mapping: dict[int, Any] = {}

    for vid, var in model.vars.items():
        if var.is_bool:
            mapping[vid] = out.NewBoolVar(var.name)
        else:
            mapping[vid] = out.NewIntVar(var.lo, var.hi, var.name)

    ctx = _Ctx(out, mapping)
    for constraint in model.constraints:
        _assert(constraint, ctx, None)
    return out, mapping


@dataclass(slots=True)
class _Ctx:
    """编译上下文：目标模型、变量映射、辅助变量计数。"""

    out: Any
    mapping: dict[int, Any]
    aux_count: int = 0

    def new_aux(self, tag: str):
        self.aux_count += 1
        return self.out.NewBoolVar(f"aux_{tag}_{self.aux_count}")


def _lin(mapping: dict[int, Any], expr: Lin):
    """线性式 → CP-SAT 表达式（纯 Python 求和，CP-SAT 会自行线性化）。"""
    result = expr.const
    for vid, coeff in expr.terms:
        result = result + coeff * mapping[vid]
    return result


def _assert(node: object, ctx: _Ctx, enforcement: Any) -> None:
    """断言 `node` 为真（可选地在 `enforcement` 成立时）。

    与 `_bool_expr` 的区别：这里直接生成约束，**不引入辅助变量**
    （除非表达式结构确实需要）。顶层约束走这条路径，效率最高。
    """
    out, mapping = ctx.out, ctx.mapping

    if isinstance(node, BConst):
        if not node.value:
            raise ValueError("不可满足的常量断言（False）")
        return

    if isinstance(node, BVar):
        constraint = mapping[node.vid] == 1
        if enforcement is None:
            out.Add(constraint)
        else:
            out.Add(constraint).OnlyEnforceIf(enforcement)
        return

    if isinstance(node, Cmp):
        constraint = _cmp(_lin(mapping, node.lhs), node.op, _lin(mapping, node.rhs))
        if enforcement is None:
            out.Add(constraint)
        else:
            out.Add(constraint).OnlyEnforceIf(enforcement)
        return

    if isinstance(node, Not):
        # ¬x 为真 ⟺ x 为假
        _assert_false(node.x, ctx, enforcement)
        return

    if isinstance(node, And):
        for arg in node.args:
            _assert(arg, ctx, enforcement)
        return

    if isinstance(node, Or):
        literals = [_bool_expr(arg, ctx) for arg in node.args]
        if enforcement is None:
            out.AddBoolOr(literals)
        else:
            out.AddBoolOr(literals).OnlyEnforceIf(enforcement)
        return

    if isinstance(node, Xor):
        a, b = _bool_expr(node.a, ctx), _bool_expr(node.b, ctx)
        out.Add(a != b)
        return

    if isinstance(node, Imp):
        # a ⇒ b  等价于  ¬a ∨ b
        literals = [_bool_expr(node.a, ctx).Not(), _bool_expr(node.b, ctx)]
        if enforcement is None:
            out.AddBoolOr(literals)
        else:
            out.AddBoolOr(literals).OnlyEnforceIf(enforcement)
        return

    if isinstance(node, Iff):
        # reify：a ⇔ b，用变量等价表达（CP-SAT 原生支持）
        a, b = _bool_expr(node.a, ctx), _bool_expr(node.b, ctx)
        if enforcement is None:
            out.Add(a == b)
        else:
            out.Add(a == b).OnlyEnforceIf(enforcement)
        return

    if isinstance(node, AllDiff):
        out.AddAllDifferent([_lin(mapping, e) for e in node.args])
        return

    if isinstance(node, ModEq):
        out.AddModuloEquality(_lin(mapping, node.b), _lin(mapping, node.a), node.m)
        return

    if isinstance(node, AllowedAssignments):
        exprs = [_lin(mapping, e) for e in node.lins]
        out.AddAllowedAssignments(exprs, [list(t) for t in node.tuples])
        return

    raise TypeError(f"不支持的 IR 节点: {type(node).__name__}")


def _assert_false(node: object, ctx: _Ctx, enforcement: Any) -> None:
    """断言 `node` 为假。"""
    out, mapping = ctx.out, ctx.mapping

    if isinstance(node, BConst):
        if node.value:
            raise ValueError("不可满足的常量断言（¬True）")
        return

    if isinstance(node, BVar):
        constraint = mapping[node.vid] == 0
        if enforcement is None:
            out.Add(constraint)
        else:
            out.Add(constraint).OnlyEnforceIf(enforcement)
        return

    if isinstance(node, Not):
        _assert(node.x, ctx, enforcement)
        return

    if isinstance(node, And):
        # ¬(a ∧ b) ≡ ¬a ∨ ¬b
        literals = [_bool_expr(arg, ctx).Not() for arg in node.args]
        if enforcement is None:
            out.AddBoolOr(literals)
        else:
            out.AddBoolOr(literals).OnlyEnforceIf(enforcement)
        return

    if isinstance(node, Or):
        # ¬(a ∨ b) ≡ ¬a ∧ ¬b
        for arg in node.args:
            _assert_false(arg, ctx, enforcement)
        return

    if isinstance(node, Cmp):
        constraint = _cmp(
            _lin(mapping, node.lhs), _NEGATED[node.op], _lin(mapping, node.rhs)
        )
        if enforcement is None:
            out.Add(constraint)
        else:
            out.Add(constraint).OnlyEnforceIf(enforcement)
        return

    # 兜底：求值后取反
    out.Add(_bool_expr(node, ctx) == 0)


def _bool_expr(node: object, ctx: _Ctx) -> Any:
    """返回表示 `node` 真值的 CP-SAT 布尔变量（必要时引入辅助变量）。"""
    out, mapping = ctx.out, ctx.mapping

    if isinstance(node, BVar):
        return mapping[node.vid]

    if isinstance(node, BConst):
        aux = ctx.new_aux("const")
        out.Add(aux == (1 if node.value else 0))
        return aux

    if isinstance(node, Not):
        return _bool_expr(node.x, ctx).Not()

    if isinstance(node, Cmp):
        aux = ctx.new_aux("cmp")
        true_c = _cmp(_lin(mapping, node.lhs), node.op, _lin(mapping, node.rhs))
        false_c = _cmp(
            _lin(mapping, node.lhs), _NEGATED[node.op], _lin(mapping, node.rhs)
        )
        out.Add(true_c).OnlyEnforceIf(aux)
        out.Add(false_c).OnlyEnforceIf(aux.Not())
        return aux

    if isinstance(node, And):
        aux = ctx.new_aux("and")
        literals = [_bool_expr(arg, ctx) for arg in node.args]
        out.AddBoolAnd(literals).OnlyEnforceIf(aux)
        out.AddBoolOr([lit.Not() for lit in literals]).OnlyEnforceIf(aux.Not())
        return aux

    if isinstance(node, Or):
        aux = ctx.new_aux("or")
        literals = [_bool_expr(arg, ctx) for arg in node.args]
        out.AddBoolOr(literals).OnlyEnforceIf(aux)
        out.AddBoolAnd([lit.Not() for lit in literals]).OnlyEnforceIf(aux.Not())
        return aux

    if isinstance(node, Xor):
        aux = ctx.new_aux("xor")
        a, b = _bool_expr(node.a, ctx), _bool_expr(node.b, ctx)
        out.Add(a != b).OnlyEnforceIf(aux)
        out.Add(a == b).OnlyEnforceIf(aux.Not())
        return aux

    if isinstance(node, (Imp, Iff)):
        aux = ctx.new_aux(node.__class__.__name__.lower())
        a, b = _bool_expr(node.a, ctx), _bool_expr(node.b, ctx)
        if isinstance(node, Imp):
            out.AddBoolOr([a.Not(), b]).OnlyEnforceIf(aux)
            out.AddBoolAnd([a, b.Not()]).OnlyEnforceIf(aux.Not())
        else:
            out.Add(a == b).OnlyEnforceIf(aux)
            out.Add(a != b).OnlyEnforceIf(aux.Not())
        return aux

    raise TypeError(f"不支持的 IR 节点: {type(node).__name__}")


_NEGATED = {"==": "!=", "!=": "==", "<=": ">", ">": "<=", "<": ">=", ">=": "<"}


def _cmp(lhs, op: str, rhs):
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


def _make_solver(config: SolverConfig) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = config.num_workers
    solver.parameters.random_seed = config.random_seed
    solver.parameters.linearization_level = config.linearization_level
    solver.parameters.randomize_search = config.randomize_search
    if config.max_time_seconds > 0:
        solver.parameters.max_time_in_seconds = config.max_time_seconds
    return solver


def solve(
    model: Model, config: SolverConfig | None = None
) -> SolveResult:
    """求解 IR 模型，返回一组解。"""
    config = config or SolverConfig()
    cp, mapping = compile_model(model)
    solver = _make_solver(config)
    status = solver.Solve(cp)
    name = solver.StatusName(status)

    values = {vid: solver.Value(var) for vid, var in mapping.items() if vid >= 0}
    return SolveResult(status=name, values=values, wall_time=solver.WallTime())


def solve_all(
    model: Model,
    config: SolverConfig | None = None,
    limit: int | None = None,
) -> tuple[list[SolveResult], bool]:
    """枚举全部解（no-good 切割）。

    借鉴 fanmade 实证做法：每求得一解就追加排除该解的析取约束，
    直到无解为止。返回 (解列表, 是否完整枚举)。
    """
    config = config or SolverConfig()
    results: list[SolveResult] = []
    complete = True

    while True:
        if limit is not None and len(results) >= limit:
            complete = False
            break
        result = solve(model, config)
        if not result.satisfiable:
            break
        results.append(result)

        # 排除当前解：至少一个变量取值不同
        clause = []
        for vid, value in result.values.items():
            var = model.vars[vid]
            if var.is_bool:
                clause.append(BVar(vid) if value == 0 else Not(BVar(vid)))
            else:
                clause.append(Cmp("!=", Lin(((vid, 1),)), Lin((), value)))
        model.add(Or(tuple(clause)))

    return results, complete
