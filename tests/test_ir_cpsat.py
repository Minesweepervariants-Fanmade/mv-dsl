"""IR 与 CP-SAT 后端的基础验证。"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from mv_dsl.backends.cpsat import solve, solve_all
from mv_dsl.ir.expr import (
    AllDiff,
    And,
    BVar,
    Cmp,
    Iff,
    Lin,
    Model,
    ModEq,
    Not,
    Or,
    exactly_one,
    sum_of,
)


def test_bool_basics():
    m = Model()
    a, b = m.new_bool("a"), m.new_bool("b")
    m.add(a)
    m.add(Cmp("==", Lin(((b.vid, 1),), 0), Lin((), 0)))
    r = solve(m)
    assert r.satisfiable
    assert r.values[a.vid] == 1
    assert r.values[b.vid] == 0


def test_sum_equals_count():
    """雷计数约束：五个布尔中恰有三个为真。"""
    m = Model()
    cells = [m.new_bool(f"c{i}") for i in range(5)]
    m.add(Cmp("==", sum_of(Lin(((c.vid, 1),)) for c in cells), Lin((), 3)))
    r = solve(m)
    assert r.satisfiable
    assert sum(r.values[c.vid] for c in cells) == 3


def test_reify_conditional():
    """reify：开关为真时约束生效。"""
    m = Model()
    x = m.new_bool("x")
    switch = m.new_bool("switch")
    m.add(switch)
    m.add(Iff(switch, Cmp("==", Lin(((x.vid, 1),)), Lin((), 1))))
    r = solve(m)
    assert r.satisfiable
    assert r.values[switch.vid] == 1
    assert r.values[x.vid] == 1


def test_reify_off_leaves_free():
    """开关为假时约束不生效——x 应保持自由（求解器可任取，这里只验证可解）。"""
    m = Model()
    x = m.new_bool("x")
    switch = m.new_bool("switch")
    m.add(Not(switch))
    m.add(Iff(switch, Cmp("==", Lin(((x.vid, 1),)), Lin((), 1))))
    assert solve(m).satisfiable


def test_liar_offset():
    """误差规则：真实计数与显示值相差 ±1。"""
    m = Model()
    cells = [m.new_bool(f"c{i}") for i in range(4)]
    shown = 2
    m.add(
        Or(
            (
                Cmp("==", sum_of(Lin(((c.vid, 1),)) for c in cells), Lin((), shown + 1)),
                Cmp("==", sum_of(Lin(((c.vid, 1),)) for c in cells), Lin((), shown - 1)),
            )
        )
    )
    r = solve(m)
    assert r.satisfiable
    total = sum(r.values[c.vid] for c in cells)
    assert total in (shown + 1, shown - 1)


def test_modulo():
    """取模规则 [2M]：计数 ≡ 显示值 (mod 3)。"""
    m = Model()
    cells = [m.new_bool(f"c{i}") for i in range(9)]
    m.add(
        ModEq(
            sum_of(Lin(((c.vid, 1),)) for c in cells),
            3,
            Lin((), 1),
        )
    )
    r = solve(m)
    assert r.satisfiable
    assert sum(r.values[c.vid] for c in cells) % 3 == 1


def test_alldiff_and_exactly_one():
    m = Model()
    xs = [m.new_int(f"x{i}", 0, 3) for i in range(3)]
    m.add(AllDiff(tuple(xs)))
    flags = [m.new_bool(f"f{i}") for i in range(3)]
    m.add(exactly_one(flags))
    r = solve(m)
    assert r.satisfiable
    vals = [r.values[x.terms[0][0]] for x in xs]
    assert len(set(vals)) == 3
    assert sum(r.values[f.vid] for f in flags) == 1


def test_count_solutions():
    """全解枚举：三个布尔、恰一个为真 → 3 个解。"""
    m = Model()
    cells = [m.new_bool(f"c{i}") for i in range(3)]
    m.add(Cmp("==", sum_of(Lin(((c.vid, 1),)) for c in cells), Lin((), 1)))
    results, complete = solve_all(m)
    assert complete
    assert len(results) == 3


def test_unique_solution_detection():
    """唯一性验证：no-good 切割后应无第二解。"""
    m = Model()
    cells = [m.new_bool(f"c{i}") for i in range(3)]
    for c in cells:
        m.add(c)
    results, complete = solve_all(m)
    assert complete
    assert len(results) == 1


def test_infeasible():
    m = Model()
    x = m.new_bool("x")
    m.add(x)
    m.add(Not(x))
    r = solve(m)
    assert r.status == "INFEASIBLE"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("全部通过")
