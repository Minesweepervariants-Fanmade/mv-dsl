"""mv2 非副板类线索规则验证：答案盘必须满足全部约束。

筛选含目标规则（2X/2X'/2D/2D'/2M/2P）且不含副板规则（2E/2L/2E^/2L'/2E'/2I/2U）
的官方关卡，把答案盘代入编译结果检查。
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

WANT = {"2X", "2X'", "2D", "2D'", "2M", "2P"}
EXCLUDE = {"2E", "2L", "2E^", "2L'", "2E'", "2I", "2U", "2U'"}


def pick(count: int = 30) -> list:
    picked, seen = [], set()
    with open(PATH, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0 or not line.strip():
                continue
            rules = parse_level_id(line.split("\t")[0])[0]
            if not (WANT & set(rules)) or EXCLUDE & set(rules):
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


def main(count: int = 30) -> int:
    puzzles = pick(count)
    t0 = time.time()
    ok = fail = 0
    covered: set[str] = set()

    for p in puzzles:
        compiled = compile_puzzle(p)
        if compiled.skipped:
            print(f"  跳过 {p.level_id}: {compiled.skipped}")
            continue
        covered.update(r for r in p.rules if r in WANT)

        # 优先 IR 直算；含辅助变量（如 2P 无，但 2X 用 And/Or 无变量）回退 CP-SAT
        try:
            bad = violations(compiled.model, Assignment(compiled.assignment_from_answer(p)))
        except KeyError:
            for (r, c), vid in compiled.mine_vars.items():
                compiled.model.add(
                    Cmp("==", Lin(((vid, 1),)), Lin((), 1 if p.cells[r][c].mine else 0))
                )
            bad = [] if solve(compiled.model).satisfiable else [-1]

        if bad:
            fail += 1
            print(f"  ✗ {p.level_id} {p.rules} {len(bad)} 条违反")
        else:
            ok += 1

    print(f"\nmv2 非副板线索规则验证：通过 {ok}  违反 {fail}  覆盖规则 {sorted(covered)}")
    print(f"耗时 {time.time() - t0:.1f}s")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 30))
