#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# 2B Bridge 反例 + fanmade 4 种实现准确性与性能对比
#
# 背景：官方 [2B] 实现（mv2_solver_dump.cs 2738-2819）用三组约束：
#   1. 每列雷数 == MineCount/SizeX（列平衡）
#   2. 每个雷左/右列三格至少一个雷（局部邻接）
#   3. 横向空隙（(y,x),(y,x-1) 非雷）→ 上方两列累计雷数相等（空隙平衡）
# 约束 3 只能检测「空隙处」的前缀差，无法约束「成块错位」的雷
# （第 i 桥行差 >= 2 但每行都有雷挡住空隙时检测不到）→ 假 SAT。
#
# 本脚本：构造 9x9 k=4 的合法/非法桥布局，对比官方同构实现（MVDSL bridge2）
# 与 fanmade 4 种实现（nt/real/xqbk/hhy）的判定正确性与求解时间。
import os
import sys
import time
import importlib.util
import importlib.machinery
import types

_FANMADE = r"D:/dev/mv/Minesweepervariants-Fanmade"          # 研究依赖（fanmade 仓库，硬编码）
_ROOT = _FANMADE
_RULE = os.path.join(_ROOT, "rule")
_MV = os.path.join(_ROOT, "MinesweeperVariants")
_MVPKG = os.path.join(_MV, "minesweepervariants")
sys.path.insert(0, _MV)


def _make_pkg(name: str, path: str) -> types.ModuleType:
    p = types.ModuleType(name)
    init = os.path.join(path, "__init__.py")
    if os.path.exists(init):
        p.__file__ = init
    p.__path__ = [path]
    p.__package__ = name
    p.__spec__ = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, init)
    )
    sys.modules[name] = p
    return p


_make_pkg("minesweepervariants", _MVPKG)
for _sub in ("abs", "config", "impl", "utils"):
    _make_pkg(f"minesweepervariants.{_sub}", os.path.join(_MVPKG, _sub))
_make_pkg("minesweepervariants.impl.board", os.path.join(_MVPKG, "impl/board"))
_make_pkg("minesweepervariants.impl.summon", os.path.join(_MVPKG, "impl/summon"))
_make_pkg("minesweepervariants.impl", os.path.join(_MVPKG, "impl"))
_make_pkg("minesweepervariants.impl.rule", _RULE)
for _sub in ("abs", "Rrule", "Lrule", "Mrule", "rule3D", "sharpRule", "utils", "image"):
    _make_pkg(f"minesweepervariants.impl.rule.{_sub}", os.path.join(_RULE, _sub))

import importlib as _il  # noqa: E402

_solver = _il.import_module("minesweepervariants.impl.summon.solver")
Switch = _solver.Switch
board_create_constraints = _solver.board_create_constraints

from ortools.sat.python import cp_model  # noqa: E402
from minesweepervariants.board import Board, MASTER_BOARD_KEY, Position  # noqa: E402
from minesweepervariants.size import Size  # noqa: E402
from minesweepervariants.utils.impl_obj import MINES_TAG  # noqa: E402

# 2B.py 顶层 import solver → recursive_import 时循环导入失败被吞，
# 需 solver 完整加载后手动 spec 加载（同 2A 的处理方式）
_2b_spec = importlib.util.spec_from_file_location(
    "minesweepervariants.impl.rule.Lrule.2B",
    os.path.join(_RULE, "Lrule", "2B.py"),
)
_2b_mod = importlib.util.module_from_spec(_2b_spec)
sys.modules[_2b_spec.name] = _2b_mod
_2b_spec.loader.exec_module(_2b_mod)
Rule2B = _2b_mod.Rule2B

# --- MVDSL 官方同构实现 ---
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from mv_dsl.puzzle.model import Cell, Puzzle  # noqa: E402
from mv_dsl.rules.compiler import compile_puzzle  # noqa: E402
from mv_dsl.backends.cpsat import solve as mvsolve  # noqa: E402
from mv_dsl.ir.expr import Cmp, Lin  # noqa: E402


def make_board(n: int, mines: set) -> Board:
    """mines: set of (col, row)"""
    board = Board()
    board.generate_board(MASTER_BOARD_KEY, size=Size(rows=n, cols=n))
    for c, r in mines:
        board.set_value(Position(c, r, MASTER_BOARD_KEY), MINES_TAG)
    return board


# --- 布局构造（(col, row)）---
def horizontal_bridges(n: int, rows: set) -> set:
    return {(c, r) for c in range(n) for r in rows}


def block_shift(n: int, rows_even: set, rows_odd: set) -> set:
    mines = set()
    for c in range(n):
        rows = rows_even if c % 2 == 0 else rows_odd
        for r in rows:
            mines.add((c, r))
    return mines


LAYOUTS = [
    # (名称, 尺寸, 雷集合, 期望: True=SAT 合法)
    ("L1 合法·水平4桥", 9, horizontal_bridges(9, {1, 3, 5, 7}), True),
    ("L3 合法·锯齿4桥", 9, block_shift(9, {1, 3, 5, 7}, {2, 4, 6, 8}), True),
    ("L2 非法·断桥错位", 9, block_shift(9, {1, 2, 3, 4}, {3, 4, 5, 6}), False),
    # 精细错位：第 3/4 桥行差 2（5↔7, 6↔8），但每个雷左右有邻、
    # 空隙行全部被雷覆盖 → 官方空隙平衡检测不到
    ("L4 非法·中段断桥", 9,
     {(0, 1), (0, 3), (0, 5), (0, 6)}
     | {(c, r) for c in range(1, 9) for r in (2, 4, 7, 8)}, False),
    # 枚举出的漏检列对 (0,1,2,4)↔(0,3,4,5) 拼完整盘（列 1-8 相同，其余列对合法）
    ("L7 非法·枚举反例", 9,
     {(0, r) for r in (0, 1, 2, 4)}
     | {(c, r) for c in range(1, 9) for r in (0, 3, 4, 5)}, False),
    ("L6 合法·k2交错", 5, block_shift(5, {1, 3}, {2, 4}), True),
    ("L5 非法·k2错位", 5, block_shift(5, {1, 2}, {3, 4}), False),
]


def run_fanmade(impl: str, n: int, mines: set) -> tuple[bool, float]:
    board = make_board(n, mines)
    rule = Rule2B(data=impl)
    model, switch, _ = board_create_constraints(board, [rule], drop_r=False)
    for v in switch.all_vars:
        model.Add(v == 1)
    for r in range(n):
        for c in range(n):
            v = board.get_variable(Position(c, r, MASTER_BOARD_KEY))
            model.Add(v == (1 if (c, r) in mines else 0))
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 8
    t0 = time.time()
    st = solver.Solve(model)
    dt = time.time() - t0
    return st in (cp_model.FEASIBLE, cp_model.OPTIMAL), dt


def run_official(n: int, mines_cr: set) -> tuple[bool, float]:
    """MVDSL bridge2.py（官方同构）。mines_cr: set of (col, row)"""
    cells = tuple(
        tuple(Cell(mine=(c, r) in mines_cr) for c in range(n)) for r in range(n)
    )
    puzzle = Puzzle(
        source="bench", level_id="2B-bench", rules=("2B",),
        width=n, height=n, cells=cells, mine_count=len(mines_cr),
    )
    compiled = compile_puzzle(puzzle)
    if compiled.skipped:
        return False, 0.0
    for (r, cc), vid in compiled.mine_vars.items():
        compiled.model.add(Cmp("==", Lin(((vid, 1),)), Lin((), 1 if puzzle.cells[r][cc].mine else 0)))
    t0 = time.time()
    ok = mvsolve(compiled.model).satisfiable
    return ok, time.time() - t0


def bench_open(impl: str, n: int, mines: set, reps: int = 3) -> float:
    """开放求解：不固定雷，只加雷数约束 + 2B 约束，返回最小求解时间。"""
    best = float("inf")
    for _ in range(reps):
        board = make_board(n, mines)
        rule = Rule2B(data=impl)
        model, switch, _ = board_create_constraints(board, [rule], drop_r=False)
        for v in switch.all_vars:
            model.Add(v == 1)
        model.Add(sum(board.get_variable(Position(c, r, MASTER_BOARD_KEY))
                      for r in range(n) for c in range(n)) == len(mines))
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 8
        t0 = time.time()
        solver.Solve(model)
        best = min(best, time.time() - t0)
    return best


def bench_open_official(n: int, mines_cr: set, reps: int = 3) -> float:
    best = float("inf")
    for _ in range(reps):
        cells = tuple(
            tuple(Cell(mine=(c, r) in mines_cr) for c in range(n)) for r in range(n)
        )
        puzzle = Puzzle(
            source="bench", level_id="2B-bench", rules=("2B",),
            width=n, height=n, cells=cells, mine_count=len(mines_cr),
        )
        compiled = compile_puzzle(puzzle)
        t0 = time.time()
        mvsolve(compiled.model)
        best = min(best, time.time() - t0)
    return best


def main() -> int:
    print(f"{'布局':<16}{'期望':<6}{'官方(bridge2)':<22}{'nt':<22}{'real':<22}{'xqbk':<22}{'hhy':<22}")
    print("-" * 120)
    for name, n, mines, expect in LAYOUTS:
        line = f"{name:<14}{'SAT' if expect else 'UNSAT':<6}"
        # 官方同构
        ok_o, t_o = run_official(n, mines)
        line += f"{('✓' if ok_o == expect else '✗')} {'SAT' if ok_o else 'UNSAT'}({t_o*1000:.0f}ms){'':<4}"
        # fanmade 4 种（real 的 data 是 "wu"）
        for impl, data in (("nt", "nt"), ("real", "wu"), ("xqbk", "xqbk"), ("hhy", "hhy")):
            try:
                ok, t = run_fanmade(data, n, mines)
                mark = "✓" if ok == expect else "✗"
            except Exception as e:  # noqa: BLE001
                ok, t, mark = False, 0.0, f"ERR:{str(e)[:12]}"
            line += f"{mark} {'SAT' if ok else 'UNSAT'}({t*1000:.0f}ms){'':<4}"
        print(line)

    print()
    print("=== 开放求解性能（9x9 k=4，只给雷数约束，多次取最小）===")
    perf_mines = horizontal_bridges(9, {1, 3, 5, 7})
    print(f"官方(bridge2): {bench_open_official(9, perf_mines)*1000:.1f}ms")
    for impl, data in (("nt", "nt"), ("real", "wu"), ("xqbk", "xqbk"), ("hhy", "hhy")):
        try:
            print(f"{impl:<14}: {bench_open(data, 9, perf_mines)*1000:.1f}ms")
        except Exception as e:  # noqa: BLE001
            print(f"{impl:<14}: ERR {e}")
    print()
    print("✓=判定正确  ✗=判定错误（官方 ✗ 即 4 桥缺陷证据）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
