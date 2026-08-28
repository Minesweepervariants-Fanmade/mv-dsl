"""把谜题（L3）编译为后端无关约束（L1）。

线索规则的约束由组合子管道生成（`ClueRule.encode`）——**本文件不含任何规则语义**，
只负责调度：遍历格子 → 查注册表 → 调用管道编码。新增规则无需改动本文件。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ir.expr import Cmp, Lin, Model, sum_of
from ..puzzle.model import Clue, Puzzle
from ..registry.rules_mv1 import CONSTRAINTS as CONSTRAINTS_MV1
from ..registry.rules_mv2 import CONSTRAINTS as CONSTRAINTS_MV2
from .evaluator import UnknownRule, get_rule

# 合并两代全局规则注册表
CONSTRAINTS: dict[str, object] = {**CONSTRAINTS_MV1, **CONSTRAINTS_MV2}

__all__ = ["compile_puzzle", "CompiledPuzzle", "UnsupportedRule"]


class UnsupportedRule(Exception):
    """规则暂未实现约束生成（未注册）。"""


@dataclass(slots=True)
class CompiledPuzzle:
    model: Model
    mine_vars: dict[tuple[int, int], int]  # (row, col) → vid
    clue_vars: dict[tuple[int, int], Lin]  # (row, col) → 线索值表达式
    sideboard_vars: dict[tuple[int, int], int] = field(default_factory=dict)  # (col, row) → vid
    skipped: tuple[str, ...] = ()

    def assignment_from_answer(self, puzzle: Puzzle) -> dict[int, int]:
        """用官方答案盘生成完整赋值（线索值取显示值，含副板雷）。"""
        values: dict[int, int] = {}
        for (r, c), vid in self.mine_vars.items():
            values[vid] = 1 if puzzle.cells[r][c].mine else 0
        for (col, row), vid in self.sideboard_vars.items():
            values[vid] = 1 if puzzle.sideboard.cells[row][col].lower().startswith("f") else 0
        # [2E] 置换雷行位置变量（perm[col]）：副板该列雷行
        perm = self.model.extras.get("perm")
        if perm is not None and puzzle.sideboard is not None:
            for col, row_pos in perm.items():
                vid = row_pos.terms[0][0]
                rows = [
                    r
                    for r in range(puzzle.sideboard.height)
                    if puzzle.sideboard.cells[r][col].lower().startswith("f")
                ]
                values[vid] = rows[0] if rows else 0
        for (r, c), expr in self.clue_vars.items():
            cell = puzzle.cells[r][c]
            if cell.clue is None or cell.clue.value is None:
                continue
            value = cell.clue.value
            if isinstance(value, tuple):
                continue  # 数墙等多值线索，暂不参与数值赋值
            values[expr.terms[0][0]] = value
        return values


def build_permutation(model: Model, puzzle: Puzzle) -> dict[int, Lin]:
    """构建 [2E] 副板置换变量体系。

    副板每列恰 1 雷，雷行位置（0-based）即该列加密值的真实值。
    返回 `{列: 雷行位置 Lin}`；副板格变量存入 `model.extras["perm_cells"]`
    供 [2EP] 逐行绑定使用。
    """
    sb = puzzle.sideboard
    if sb is None:
        raise ValueError("[2E] 需要副板（置换矩阵）")
    perm: dict[int, Lin] = {}
    perm_cells: dict[tuple[int, int], int] = {}
    for col in range(sb.width):
        col_vars: list[int] = []
        for row in range(sb.height):
            vid = model.new_bool(f"sb_{col}_{row}").vid
            col_vars.append(vid)
            perm_cells[(col, row)] = vid
        # 每列恰 1 雷
        model.add(
            Cmp("==", sum_of(Lin(((v, 1),)) for v in col_vars), Lin((), 1))
        )
        # 雷行位置 = Σ row × 该行雷
        row_pos = model.new_int(f"perm_{col}", 0, sb.height - 1)
        model.add(
            Cmp(
                "==",
                row_pos,
                sum_of(Lin(((col_vars[row], row),)) for row in range(sb.height)),
            )
        )
        perm[col] = row_pos
    model.extras["perm"] = perm
    model.extras["perm_cells"] = perm_cells
    return perm


def build_liar_marks(model: Model, puzzle: Puzzle) -> dict[tuple[int, int], int]:
    """构建 [2L] 系误差副板变量：主格 (row, col) 说谎 ⟺ 副板 (row, col+offset) 是雷。

    官方（mv2 反编译 BuildMetaConstraints 2068-2124 行）：2L 副板是**置换矩阵**
    （每行每列恰 1 雷，即每行每列恰一个误差格），逐格对应主板——主格 (i,j) 的
    liar 状态 = `isBomb[i, j + LiarBoardOffset]`。liar 板位于副板**最后** SizeX 列
    （[2E][2L] 分离副板 `[&&]` 时 2E 板在前 SizeX 列，offset = SizeX）。

    返回 `{(row, col): vid}`；副板格变量存入 `model.extras["liar_cells"]`。
    """
    sb = puzzle.sideboard
    if sb is None or sb.width < puzzle.width:
        raise ValueError("[2L] 需要逐格对应的误差副板（宽 >= 主板边长）")
    offset = sb.width - puzzle.width
    liar_cells: dict[tuple[int, int], object] = {}
    for row in range(puzzle.height):
        for col in range(puzzle.width):
            bv = model.new_bool(f"liar_{row}_{col}")
            liar_cells[(row, col)] = bv
    # 每行恰 1 雷、每列恰 1 雷（置换矩阵）
    for row in range(puzzle.height):
        model.add(
            Cmp(
                "==",
                sum_of(Lin(((liar_cells[(row, c)].vid, 1),)) for c in range(puzzle.width)),
                Lin((), 1),
            )
        )
    for col in range(puzzle.width):
        model.add(
            Cmp(
                "==",
                sum_of(Lin(((liar_cells[(r, col)].vid, 1),)) for r in range(puzzle.height)),
                Lin((), 1),
            )
        )
    model.extras["liar_cells"] = liar_cells
    model.extras["liar_offset"] = offset
    return {pos: bv.vid for pos, bv in liar_cells.items()}


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

    # 全局规则（Constraint 子类）——按 puzzle.rules 逐条生成
    for rule_id in puzzle.rules:
        constraint = CONSTRAINTS.get(rule_id)
        if constraint is not None:
            try:
                model.add(constraint.encode(model, puzzle, mine_vars))
            except Exception as exc:  # noqa: BLE001
                skipped.append(f"[{rule_id}] {exc}")

    # 2A 面积规则：预构建四连通分量变量体系（A2Area.encode 消费）。
    # 含 [2EA]/[2LA]（加密/误差 ∘ 面积）组合时同样需要（规则级无 "2A"）。
    needs_components = "2A" in puzzle.rules or any(
        cell.clue is not None
        and (cell.clue.rule.startswith("2EA") or cell.clue.rule.startswith("2LA"))
        for _, _, cell in puzzle.iter_cells()
    )
    if needs_components:
        from ..combinators.constraint.connectivity import build_components

        model.extras["components"] = build_components(model, puzzle, mine_vars)

    # [2E] 加密规则：预构建副板置换变量体系（RelationEncrypted / A2Cross /
    # A2Product / A2Area 消费）。副板列 = 加密值，雷行位置 = 真实值。
    sideboard_vars: dict[tuple[int, int], int] = {}
    if "2E" in puzzle.rules:
        try:
            perm = build_permutation(model, puzzle)
            sideboard_vars.update(model.extras["perm_cells"])
        except ValueError as exc:
            skipped.append(f"[2E] {exc}")

    # [2L] 误差副板：置换矩阵（每行每列恰 1 雷），主格 liar 状态 = 副板对应格。
    # RelationLiarModulo（2LM）消费；副板格变量并入 sideboard_vars 供答案赋值。
    if "2L" in puzzle.rules:
        try:
            liar_cells = build_liar_marks(model, puzzle)
            offset = model.extras["liar_offset"]
            sideboard_vars.update(
                {(col + offset, row): vid for (row, col), vid in liar_cells.items()}
            )
        except ValueError as exc:
            skipped.append(f"[2L] {exc}")

    # 逐线索格生成约束
    for r, c, cell in puzzle.iter_cells():
        if cell.clue is None:
            continue
        clue = cell.clue

        if clue.value is None:
            # mv1 的线索值不在文件中，需先 fill（依赖显示值的规则无法编码）
            skipped.append(f"[{clue.rule}] 线索值缺失（mv1 需先 fill）")
            continue

        if not isinstance(clue.value, tuple):
            value_var = model.new_int(f"clue_{r}_{c}", clue.value, clue.value)
        else:
            value_var = model.new_int(f"clue_{r}_{c}", 0, 64)
        clue_vars[(r, c)] = value_var

        try:
            model.add(_clue_constraint(model, puzzle, r, c, clue, mine_vars, value_var))
        except UnknownRule as exc:
            skipped.append(str(exc))
        except NotImplementedError as exc:
            skipped.append(f"[{clue.rule}] {exc}")

    return CompiledPuzzle(
        model=model,
        mine_vars=mine_vars,
        clue_vars=clue_vars,
        sideboard_vars=sideboard_vars,
        skipped=tuple(skipped),
    )
