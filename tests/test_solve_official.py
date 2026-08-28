"""端到端求解验证：不用答案盘，让 CP-SAT 从线索反推雷布局。

检验项：
1. 可解性——求解器能求出解
2. 合法性——求出的解与官方答案盘**同为**约束的解
   （答案盘必然满足约束，见 test_verify_official.py，已 100% 通过）
3. 唯一性——no-good 切割后是否只有一解（仅作统计，非断言）

**重要领域事实**：14mv 是**交互式游戏**而非纸笔谜题——玩家通过点击揭示
格子逐步获得信息，而官方文件中「未揭示格」（`q`）的线索值并不存在。
因此官方关卡**不保证静态唯一解**：仅凭文件中给出的线索，往往存在多个
满足约束的雷布局。「解 == 答案盘」只在信息量足够的关卡成立。
唯一解是**出题器**（如 fanmade 的动态挖洞）的要求，不是官方关卡的性质。

分两组对比：
- A 组「纯线索规则」：约束完整
- B 组「含全局规则」：全局规则（连通/无三连等）尚未实现，约束更弱、解更多
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

sys.path.insert(0, "src")

from mv_dsl.backends.cpsat import solve, solve_all
from mv_dsl.puzzle.importer_mv1 import import_puzzle, parse_level_id
from mv_dsl.puzzle.model import Cell, Clue, Puzzle
from mv_dsl.rules.compiler import compile_puzzle
from mv_dsl.rules.evaluator import clue_value

PATH_MV1 = r"D:\dev\mv\MineVar\puzzle\all_puzzles_dedup.txt"

# mv1 的全局（布局）规则；其余为线索规则
GLOBAL_RULES = frozenset({"Q", "C", "T", "O", "D", "S", "B", "T'", "D'", "A", "H", "U"})


def fill_mv1_clues(puzzle: Puzzle) -> Puzzle:
    """mv1 的线索值需从答案盘计算，补进 Puzzle。"""
    cells = [list(row) for row in puzzle.cells]
    changed = False
    for r, c, cell in puzzle.iter_cells():
        if cell.clue is None:
            continue
        value = clue_value(puzzle, r, c, cell.clue.rule)
        if isinstance(value, tuple):
            value = int("".join(str(s) for s in value)) if value else 0
        cells[r][c] = Cell(
            mine=cell.mine,
            clue=Clue(rule=cell.clue.rule, value=value, visible=cell.clue.visible),
            colored=cell.colored,
        )
        changed = True
    if not changed:
        return puzzle
    return Puzzle(
        source=puzzle.source,
        level_id=puzzle.level_id,
        rules=puzzle.rules,
        width=puzzle.width,
        height=puzzle.height,
        cells=tuple(tuple(row) for row in cells),
        mine_count=puzzle.mine_count,
        sideboard=puzzle.sideboard,
    )


def pick_puzzles(path: str, want_global: bool, count: int) -> list[Puzzle]:
    """关卡文件按规则分组排序，需扫描筛选出目标类别。"""
    picked: list[Puzzle] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f):
            if lineno == 0 and line.startswith("!!"):
                continue
            if not line.strip():
                continue
            rules = parse_level_id(line.split("\t")[0])[0]
            if bool(GLOBAL_RULES & set(rules)) != want_global:
                continue
            try:
                picked.append(import_puzzle(line))
            except Exception:  # noqa: BLE001
                continue
            if len(picked) >= count:
                break
    return picked


@dataclass(slots=True)
class Stats:
    total: int = 0
    solved: int = 0
    matches_answer: int = 0
    unique: int = 0
    unsupported: int = 0
    times: list = field(default_factory=list)
    examples: list = field(default_factory=list)


def run_batch(puzzles: list[Puzzle], st: Stats) -> None:
    for puzzle in puzzles:
        puzzle = fill_mv1_clues(puzzle)
        try:
            compiled = compile_puzzle(puzzle)
        except Exception as exc:  # noqa: BLE001
            st.examples.append(f"编译异常 {puzzle.level_id}: {exc}")
            continue
        if compiled.skipped:
            st.unsupported += 1
            continue

        st.total += 1
        t0 = time.time()
        result = solve(compiled.model)
        st.times.append(time.time() - t0)

        if not result.satisfiable:
            st.examples.append(f"无解 {puzzle.level_id} 规则={puzzle.rules}")
            continue
        st.solved += 1

        got = {
            pos
            for pos, vid in compiled.mine_vars.items()
            if result.values.get(vid) == 1
        }
        if got == set(puzzle.answer_mines()):
            st.matches_answer += 1
        elif len(st.examples) < 8:
            st.examples.append(
                f"解不一致 {puzzle.level_id} 规则={puzzle.rules} "
                f"求得 {len(got)} 雷 vs 答案 {len(puzzle.answer_mines())} 雷"
            )

        results, complete = solve_all(compiled.model, limit=2)
        if len(results) == 1 and complete:
            st.unique += 1


def main(per_group: int = 40) -> int:
    print("扫描关卡文件，分别采样「纯线索规则」与「含全局规则」两类...")
    pure = pick_puzzles(PATH_MV1, want_global=False, count=per_group)
    with_global = pick_puzzles(PATH_MV1, want_global=True, count=per_group)

    print(f"\n--- A 组：纯线索规则 {len(pure)} 关（约束完整，应唯一且与答案一致）---")
    st_a = Stats()
    run_batch(pure, st_a)

    print(f"\n--- B 组：含全局规则 {len(with_global)} 关（全局规则未实现，预期解不唯一）---")
    st_b = Stats()
    run_batch(with_global, st_b)

    print("\n=== 汇总 ===")
    print(
        f"A 组 纯线索规则: 可编译 {st_a.total}  求出解 {st_a.solved}  "
        f"解与答案一致 {st_a.matches_answer}  唯一解 {st_a.unique}"
    )
    print(
        f"B 组 含全局规则: 可编译 {st_b.total}  求出解 {st_b.solved}  "
        f"解与答案一致 {st_b.matches_answer}  唯一解 {st_b.unique}"
    )
    if st_a.times:
        print(f"A 组平均单次求解 {sum(st_a.times) / len(st_a.times) * 1000:.1f} ms")
    print(
        "\n注：官方关卡不保证静态唯一解（交互式揭示，未揭示格的线索值不在文件中），\n"
        "    「解与答案一致」为参考指标；正确性由 test_verify_official.py 保证。"
    )

    # 断言：约束完整的一组必须全部可解
    ok = st_a.total > 0 and st_a.solved == st_a.total
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 40))
