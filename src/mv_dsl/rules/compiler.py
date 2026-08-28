"""把谜题（L3）编译为后端无关约束（L1）。

线索规则的约束由组合子管道生成（`ClueRule.encode`）——**本文件不含任何规则语义**，
只负责调度：遍历格子 → 查注册表 → 调用管道编码。新增规则无需改动本文件。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ir.expr import Cmp, Lin, Model, sum_of
from ..puzzle.model import Clue, Puzzle
from .evaluator import UnknownRule, get_rule

__all__ = ["compile_puzzle", "CompiledPuzzle", "UnsupportedRule"]


class UnsupportedRule(Exception):
    """规则暂未实现约束生成（未注册）。"""


@dataclass(slots=True)
class CompiledPuzzle:
    model: Model
    mine_vars: dict[tuple[int, int], int]  # (row, col) → vid
    clue_vars: dict[tuple[int, int], Lin]  # (row, col) → 线索值表达式
    skipped: tuple[str, ...] = ()

    def assignment_from_answer(self, puzzle: Puzzle) -> dict[int, int]:
        """用官方答案盘生成完整赋值（线索值取显示值）。"""
        values: dict[int, int] = {}
        for (r, c), vid in self.mine_vars.items():
            values[vid] = 1 if puzzle.cells[r][c].mine else 0
        for (r, c), expr in self.clue_vars.items():
            cell = puzzle.cells[r][c]
            if cell.clue is None or cell.clue.value is None:
                continue
            value = cell.clue.value
            if isinstance(value, tuple):
                continue  # 数墙等多值线索，暂不参与数值赋值
            values[expr.terms[0][0]] = value
        return values


def _clue_constraint(
    model: Model,
    puzzle: Puzzle,
    row: int,
    col: int,
    clue: Clue,
    mine_vars: dict[tuple[int, int], int],
    clue_var: Lin,
):
    """按注册表管道生成单条线索的约束。"""
    rule = get_rule(clue.rule)
    return rule.encode(model, puzzle, row, col, mine_vars, clue_var)


def compile_puzzle(puzzle: Puzzle) -> CompiledPuzzle:
    """编译谜题为 IR 模型。线索值作为已知常量（验证/求解语义一致）。"""
    model = Model()
    mine_vars: dict[tuple[int, int], int] = {}
    clue_vars: dict[tuple[int, int], Lin] = {}
    skipped: list[str] = []

    for r in range(puzzle.height):
        for c in range(puzzle.width):
            mine_vars[(r, c)] = model.new_bool(f"mine_{r}_{c}").vid

    # 雷总数
    if puzzle.mine_count is not None:
        model.add(
            Cmp(
                "==",
                sum_of(Lin(((vid, 1),)) for vid in mine_vars.values()),
                Lin((), puzzle.mine_count),
            )
        )

    # 逐线索格生成约束
    for r, c, cell in puzzle.iter_cells():
        if cell.clue is None:
            continue
        clue = cell.clue

        if clue.value is not None and not isinstance(clue.value, tuple):
            value_var = model.new_int(f"clue_{r}_{c}", clue.value, clue.value)
        else:
            value_var = model.new_int(f"clue_{r}_{c}", 0, 64)
        clue_vars[(r, c)] = value_var

        try:
            model.add(_clue_constraint(model, puzzle, r, c, clue, mine_vars, value_var))
        except UnknownRule as exc:
            skipped.append(str(exc))

    return CompiledPuzzle(
        model=model,
        mine_vars=mine_vars,
        clue_vars=clue_vars,
        skipped=tuple(skipped),
    )
