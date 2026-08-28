"""用官方谜题验证约束编译器：把答案盘代入，检查所有约束是否成立。

这是语义正确性的核心闭环——官方关卡的**答案盘**是权威基准，
若我们编译出的约束与官方规则语义一致，答案盘必然满足全部约束。

用法：
    uv run python tests/test_verify_official.py mv1 [采样数]
    uv run python tests/test_verify_official.py mv2 [采样数]
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field

sys.path.insert(0, "src")

from mv_dsl.ir.eval import Assignment, violations
from mv_dsl.puzzle.importer_mv1 import import_file as import_mv1
from mv_dsl.puzzle.importer_mv2 import import_file as import_mv2
from mv_dsl.puzzle.model import Puzzle
from mv_dsl.rules.compiler import compile_puzzle
from mv_dsl.rules.evaluator import clue_value

PATHS = {
    "mv1": r"D:\dev\mv\MineVar\puzzle\all_puzzles_dedup.txt",
    "mv2": r"D:\dev\mv\MineVar2\puzzle\all_puzzles_dedup.txt",
}


@dataclass(slots=True)
class Report:
    total: int = 0
    ok: int = 0
    failed: int = 0
    unsupported: int = 0
    errors: int = 0
    by_rule: Counter = field(default_factory=Counter)
    failed_rules: Counter = field(default_factory=Counter)
    examples: list = field(default_factory=list)


def verify_puzzle(puzzle: Puzzle, rep: Report) -> None:
    # mv1 的线索值不在文件中，先用求值器从答案盘算出（已与 legacy 100% 交叉验证）
    if puzzle.source == "mv1":
        cells = [list(row) for row in puzzle.cells]
        filled = False
        for r, c, cell in puzzle.iter_cells():
            if cell.clue is not None:
                value = clue_value(puzzle, r, c, cell.clue.rule)
                from mv_dsl.puzzle.model import Cell, Clue

                # 数墙类规则的值为段长元组，表约束用十进制拼接编码
                if isinstance(value, tuple):
                    value = int("".join(str(s) for s in value)) if value else 0

                cells[r][c] = Cell(
                    mine=cell.mine,
                    clue=Clue(
                        rule=cell.clue.rule, value=value, visible=cell.clue.visible
                    ),
                    colored=cell.colored,
                )
                filled = True
        if filled:
            puzzle = Puzzle(
                source=puzzle.source,
                level_id=puzzle.level_id,
                rules=puzzle.rules,
                width=puzzle.width,
                height=puzzle.height,
                cells=tuple(tuple(row) for row in cells),
                mine_count=puzzle.mine_count,
                sideboard=puzzle.sideboard,
            )

    try:
        compiled = compile_puzzle(puzzle)
    except Exception as exc:  # noqa: BLE001
        rep.errors += 1
        if len(rep.examples) < 5:
            rep.examples.append(f"编译异常 {puzzle.level_id}: {exc}")
        return

    if compiled.skipped:
        rep.unsupported += 1
        for rule in compiled.skipped:
            rep.by_rule[f"[跳过] {rule}"] += 1
        return

    rep.total += 1
    for rule in puzzle.rules:
        rep.by_rule[rule] += 1

    assignment = Assignment(compiled.assignment_from_answer(puzzle))
    bad = violations(compiled.model, assignment)
    if bad:
        rep.failed += 1
        for rule in puzzle.rules:
            rep.failed_rules[rule] += 1
        if len(rep.examples) < 8:
            rep.examples.append(
                f"{puzzle.level_id} 规则={puzzle.rules} 违反 {len(bad)}/{len(compiled.model.constraints)} 条"
            )
    else:
        rep.ok += 1


def main(which: str = "mv1", sample: int = 2000) -> int:
    path = PATHS.get(which)
    if path is None:
        print(f"未知数据源: {which}（可选 mv1 / mv2）")
        return 1

    importer = import_mv1 if which == "mv1" else import_mv2
    puzzles = importer(path, limit=sample)

    rep = Report()
    for puzzle in puzzles:
        verify_puzzle(puzzle, rep)

    print(f"=== {which} 官方谜题约束验证（采样 {len(puzzles)} 关）===")
    print(f"已验证 {rep.total}  通过 {rep.ok}  违反 {rep.failed}  跳过(规则未支持) {rep.unsupported}  异常 {rep.errors}")
    if rep.total:
        print(f"通过率: {rep.ok / rep.total * 100:.2f}%")
    if rep.failed:
        print("\n违反约束的规则分布:")
        for rule, n in rep.failed_rules.most_common(10):
            print(f"  {rule}: {n}")
    if rep.examples:
        print("\n样例:")
        for e in rep.examples[:8]:
            print(f"  {e}")
    return 0 if rep.failed == 0 and rep.errors == 0 else 2


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "mv1"
    sample = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    sys.exit(main(which, sample))
