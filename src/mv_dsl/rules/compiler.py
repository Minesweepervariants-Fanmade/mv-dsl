"""把谜题（L3）编译为后端无关约束（L1）。

线索规则统一走一条管道：

$$\\text{clue} = \\mathrm{Relation}(\\mathrm{Aggregate}(\\mathrm{Weight}(\\mathrm{Region}(i,j))))$$

本模块按管道各段生成约束，**不为任何组合规则写专门分支**——
组合规则（如 `LM` = Liar ∘ Multiple）只是换用不同的区域/权重/关系组合。

约束形态分两类：

- **线性类**（sum 家族）：`Σ w·mine == 值`，直接线性约束，求解效率最高
- **结构类**（数墙、视野）：邻域到值的映射非线性和，改用表约束（后续）

误差规则 [L] / [LM] 不依赖方向后缀：官方求解器同样用
`sum == n ± 1` 表达（对照 mv2 反编译 `GetCellConstraint` 3517-3537 行），
真实值非负的约束自动覆盖了「显示值为负时翻转方向」的边界情形。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ir.expr import (
    AllowedAssignments,
    And,
    BVar,
    Cmp,
    Iff,
    Lin,
    Model,
    Not,
    Or,
    sum_of,
)
from ..puzzle.model import Clue, Puzzle
from .evaluator import WALL_ORDER, region, wall_segments_from

__all__ = ["compile_puzzle", "UnsupportedRule", "LINEAR_RULES", "STRUCTURAL_RULES"]

# 区域 + 权重 → 线性可表达的规则
LINEAR_RULES: dict[str, tuple[str, str]] = {
    "V": ("moore", "plain"),
    "L": ("moore", "plain"),      # Liar：额外加 ±1 偏移
    "M": ("moore", "dye_double"),
    "LM": ("moore", "dye_double"),  # Liar ∘ Multiple：同样加 ±1
    "X'": ("cross1", "plain"),
    "X": ("cross2", "plain"),
    "MX": ("cross2", "dye_double"),
    "K": ("knight", "plain"),
}

# 需要绝对值的线性规则：|Σ| == 值 → Σ == 值 或 Σ == -值
ABSOLUTE_RULES: dict[str, tuple[str, str]] = {
    "N": ("moore", "dye_diff"),
    "NX": ("cross2", "dye_diff"),
    "MN": ("moore", "dye_mn"),
}

# 结构类规则：值不是邻域的线性和，用表约束表达
#   W  数墙：各段长度升序拼接（如段长 1,2,3 → 123）
#   W' 最长段长度
#   P  段数
#   E / E' 视野类依赖整行整列，非局部邻域，表约束不适用（待实现）
STRUCTURAL_RULES = frozenset({"W", "W'", "P"})
VISION_RULES = frozenset({"E", "E'"})


def _wall_table(puzzle: Puzzle, row: int, col: int, rule: str):
    """枚举 8 邻全部雷布局，生成 (布局, 取值) 表。"""
    ring = [(row + dr, col + dc) for dr, dc in WALL_ORDER]
    inside_idx = [
        i
        for i, (r, c) in enumerate(ring)
        if 0 <= r < puzzle.height and 0 <= c < puzzle.width
    ]
    neighbors = [ring[i] for i in inside_idx]

    tuples = []
    for mask in range(1 << len(neighbors)):
        layout = tuple(bool(mask >> k & 1) for k in range(len(neighbors)))
        # 还原到 8 邻坐标系（越界位置为 False），再走统一的段长计算
        full = [False] * 8
        for slot, (r, c) in zip(inside_idx, neighbors):
            full[slot] = layout[neighbors.index((r, c))]
        segments = wall_segments_from(tuple(full))
        if rule == "W":
            value = int("".join(str(s) for s in segments)) if segments else 0
        elif rule == "W'":
            value = segments[-1] if segments else 0
        else:  # P：段数
            value = len(segments)
        tuples.append(tuple([1 if b else 0 for b in layout] + [value]))
    return neighbors, tuple(tuples)

# 权重函数：染色格雷计多少
_WEIGHTS = {"plain": (1, 1), "dye_double": (2, 1), "dye_diff": (1, -1), "dye_mn": (2, -1)}


class UnsupportedRule(Exception):
    """规则暂未实现约束生成。"""


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


def _weighted_sum(
    model: Model,
    puzzle: Puzzle,
    cells: list[tuple[int, int]],
    weight: str,
    mine_vars: dict[tuple[int, int], int],
) -> Lin:
    """按权重构造雷的加权和表达式。"""
    colored_coeff, plain_coeff = _WEIGHTS[weight]
    terms = []
    for r, c in cells:
        coeff = colored_coeff if puzzle.cells[r][c].colored else plain_coeff
        terms.append(Lin(((mine_vars[(r, c)], coeff),)))
    return sum_of(terms)


def _vision_chain(
    model: Model,
    cells: list[tuple[int, int]],
    mine_vars: dict[tuple[int, int], int],
    tag: str,
) -> Lin:
    """构造「某方向连续可见（非雷）格数」的表达式。

    视野规则 [E]/[E'] 依赖整行整列，无法用邻域表约束，改用**辅助变量链**：
    第 k 格可见 ⟺ 第 k-1 格可见 ∧ 第 k 格非雷，格数即这些可见标志之和。
    雷会阻挡视线——链条在遇到雷之后全部为假。
    """
    if not cells:
        return Lin()

    terms: list[Lin] = []
    prev = None
    for pos in cells:  # cells 必须按「由近及远」排列
        vis = model.new_bool(f"vis_{tag}_{pos[0]}_{pos[1]}")
        not_mine = Not(BVar(mine_vars[pos]))
        model.add(Iff(vis, not_mine if prev is None else And((prev, not_mine))))
        terms.append(Lin(((vis.vid, 1),)))
        prev = vis
    return sum_of(terms)


def _vision_constraint(
    model: Model,
    puzzle: Puzzle,
    row: int,
    col: int,
    rule: str,
    mine_vars: dict[tuple[int, int], int],
    clue_var: Lin,
):
    """视野类规则约束。

    - [E]  值 = 四方向可见格数 + 1（含自身）
    - [E'] 值 = 纵向视野 − 横向视野（带符号；符号指示更长方向）
    """
    up = _vision_chain(
        model, [(r, col) for r in range(row - 1, -1, -1)], mine_vars, "u"
    )
    down = _vision_chain(
        model, [(r, col) for r in range(row + 1, puzzle.height)], mine_vars, "d"
    )
    left = _vision_chain(
        model, [(row, c) for c in range(col - 1, -1, -1)], mine_vars, "l"
    )
    right = _vision_chain(
        model, [(row, c) for c in range(col + 1, puzzle.width)], mine_vars, "r"
    )

    value = Lin(((clue_var.terms[0][0], 1),))
    if rule == "E":
        return Cmp("==", up + down + left + right + 1, value)
    # E'：纵向 − 横向（有符号）
    return Cmp("==", up + down - (left + right), value)


def _clue_constraint(
    model: Model,
    puzzle: Puzzle,
    row: int,
    col: int,
    clue: Clue,
    mine_vars: dict[tuple[int, int], int],
    clue_var: Lin,
):
    """生成单条线索的约束。"""
    base = clue.rule.rstrip("+-")
    is_liar = clue.rule.endswith("+") or clue.rule.endswith("-")

    if base in LINEAR_RULES:
        region_kind, weight = LINEAR_RULES[base]
        cells = region(puzzle, row, col, region_kind)
        total = _weighted_sum(model, puzzle, cells, weight, mine_vars)
        if is_liar:
            # 误差规则：真实值与显示值相差 ±1（真实值非负自动排除非法情形）
            return Or(
                (
                    Cmp("==", total, Lin(((clue_var.terms[0][0], 1),), -1)),
                    Cmp("==", total, Lin(((clue_var.terms[0][0], 1),), 1)),
                )
            )
        return Cmp("==", total, Lin(((clue_var.terms[0][0], 1),)))

    if base in ABSOLUTE_RULES:
        region_kind, weight = ABSOLUTE_RULES[base]
        cells = region(puzzle, row, col, region_kind)
        total = _weighted_sum(model, puzzle, cells, weight, mine_vars)
        # |Σ| == 值
        value = Lin(((clue_var.terms[0][0], 1),))
        return Or((Cmp("==", total, value), Cmp("==", total, value * -1)))

    if base in STRUCTURAL_RULES:
        neighbors, table = _wall_table(puzzle, row, col, base)
        lins = [Lin(((mine_vars[pos], 1),)) for pos in neighbors]
        lins.append(Lin(((clue_var.terms[0][0], 1),)))
        return AllowedAssignments(tuple(lins), table)

    if base in VISION_RULES:
        return _vision_constraint(
            model, puzzle, row, col, base, mine_vars, clue_var
        )

    raise UnsupportedRule(f"未知规则 {clue.rule}")


def compile_puzzle(puzzle: Puzzle, use_answer_values: bool = True) -> CompiledPuzzle:
    """编译谜题为 IR 模型。

    Args:
        puzzle: 谜题（含答案盘与线索）
        use_answer_values: 是否把官方线索值固定为常量。
            验证时为真（检查答案盘是否满足约束）；求解时应为假（线索值已知，
            但雷布局未知——线索值本身就是已知常量，故两者一致）。
    """
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

        if use_answer_values and clue.value is not None:
            # 验证模式：线索值已知且固定
            if isinstance(clue.value, tuple):
                skipped.append(clue.rule)
                continue
            value_var = model.new_int(f"clue_{r}_{c}", clue.value, clue.value)
        else:
            value_var = model.new_int(f"clue_{r}_{c}", 0, 64)
        clue_vars[(r, c)] = value_var

        try:
            model.add(
                _clue_constraint(model, puzzle, r, c, clue, mine_vars, value_var)
            )
        except UnsupportedRule as exc:
            skipped.append(str(exc))

    return CompiledPuzzle(
        model=model,
        mine_vars=mine_vars,
        clue_vars=clue_vars,
        skipped=tuple(skipped),
    )
