"""验证 [2L][2M] 组合规则（先取模再误差）：答案盘必须满足全部约束。

用法：python tests/verify_2lm.py [count] [--all]
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "src")

from mv_dsl.backends.cpsat import solve
from mv_dsl.ir.eval import Assignment, violations
from mv_dsl.ir.expr import Cmp, Lin
from mv_dsl.puzzle.importer_mv2 import import_puzzle, parse_level_id
from mv_dsl.rules.compiler import compile_puzzle

PATH = r"D:\dev\mv\MineVar2\puzzle\all_puzzles_dedup.txt"


def pick(count: int, want_2l2m: bool = True) -> list:
    picked, seen = [], set()
    with open(PATH, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0 or not line.strip():
                continue
            rules = parse_level_id(line.split("\t")[0])[0]
            if want_2l2m and not ({"2L", "2M"} <= set(rules)):
                continue
            if not want_2l2m and not ({"2E"} & set(rules)):
                continue
            key = tuple(sorted(rules))
            if key in seen:
                continue
            seen.add(key)
            try:
                picked.append(import_puzzle(line))
            except Exception:  # noqa: BLE001
                continue
            if len(picked) >= count:
                break
    return picked


def check(p) -> tuple[bool, str]:
    compiled = compile_puzzle(p)
    if compiled.skipped:
        return False, f"skip: {compiled.skipped}"
    try:
        bad = violations(compiled.model, Assignment(compiled.assignment_from_answer(p)))
    except KeyError:
        for (r, c), vid in compiled.mine_vars.items():
            compiled.model.add(
                Cmp("==", Lin(((vid, 1),)), Lin((), 1 if p.cells[r][c].mine else 0))
            )
        bad = [] if solve(compiled.model).satisfiable else [-1]
    return (len(bad) == 0), f"{len(bad)} 条违反"


def main() -> int:
    all_flag = "--all" in sys.argv
    count = 500 if all_flag else 40
    t0 = time.time()
    puzzles = pick(count)
    ok = fail = skip = 0
    for p in puzzles:
        good, msg = check(p)
        if good:
            ok += 1
        elif msg.startswith("skip"):
            skip += 1
            print(f"  - {p.level_id}: {msg}")
        else:
            fail += 1
            print(f"  ✗ {p.level_id} {p.rules}: {msg}")
    print(f"\n2LM 验证：通过 {ok}  违反 {fail}  跳过 {skip}  共 {len(puzzles)}")
    print(f"耗时 {time.time() - t0:.1f}s")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
