"""RelationEncrypted：加密（[2E] Encrypted）——真实值经未知置换显示为字母 A-H。

谜题表示：token 数字 `0..7` 即**显示字母索引**（`2E3` → 显示 `D`），
真实值 = 副板置换表反解。置换表存放在**副板**：副板第 v 列的雷行位置
（0-based）即加密值 v 的真实值（对照 legacy `enc_dict[encrypt[c]] = r`）。

求解时置换表是变量（玩家不知道哪个字母对应哪个数字）——compiler 预构建
副板变量与「每列恰 1 雷」约束，存入 `model.extras["perm"]`：
`{列: 雷行位置 Lin}`；`apply` 用 `total == perm[显示值]`。

答案盘验证时置换表已知——`apply` 直接从 `puzzle.sideboard` 读固定表。

对照官方 `GetCellConstraint` case "[2E]"（mv2 反编译 3915-3950 行）：
区域雷数（真实值）== 副板第 显示值 列的雷行位置。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...ir.expr import Cmp, Lin, Or
from .relation import Relation

if TYPE_CHECKING:
    from ...puzzle.model import Puzzle

_ENCRYPT = "ABCDEFGH"


def permutation_from_puzzle(puzzle: "Puzzle") -> dict[int, int]:
    """从副板答案读置换表：{加密值: 真实值}（副板第 c 列雷行位置）。"""
    sb = puzzle.sideboard
    if sb is None:
        raise ValueError("[2E] 需要副板（置换矩阵）")
    enc: dict[int, int] = {}
    for c in range(sb.width):
        rows = [r for r in range(sb.height) if sb.cells[r][c].lower().startswith("f")]
        if len(rows) != 1:
            raise ValueError(f"[2E] 副板第 {c} 列应有恰 1 雷，实得 {rows}")
        enc[c] = rows[0]
    return enc


def perm_value(model, puzzle: "Puzzle", shown: int) -> Lin:
    """显示值（加密索引）→ 真实值 Lin。

    求解模式（compiler 已构建副板变量）：返回副板第 shown 列的雷行位置变量；
    验证模式：返回固定常量（副板答案已知）。
    """
    perm = model.extras.get("perm")
    if perm is not None:
        return perm[shown]
    enc = permutation_from_puzzle(puzzle)
    return Lin((), enc[shown])


class RelationEncrypted(Relation):
    id = "encrypted"

    def __init__(self, square: bool = False, offset: bool = False):
        """`square=True` 用于 [2EP]（距离积加密）：
        显示编码 <50 表示「距离积 == 置换²」（开方显示），
        >=50 表示「距离积 == 置换」（√ 前缀显示）。
        `offset=True` 用于 [2E1L]（加密 ∘ 误差）：解密后真实值 == 置换[显示] ± 1
        （方向未知，官方 2E1L 的 ±1 BoolVar）。"""
        self.square = square
        self.offset = offset

    def display(
        self, real_value, direction: int = 0, puzzle: "Puzzle | None" = None, row=None, col=None
    ) -> int:
        if puzzle is None:
            raise ValueError("RelationEncrypted.display 需要 puzzle（读副板置换表）")
        if isinstance(real_value, tuple):
            # [2E1W] 数墙：段长元组 → 单段时取段长（官方谜题仅单段，多段约束恒假）
            real_value = sum(real_value)
        enc = permutation_from_puzzle(puzzle)
        if self.square:
            # 2EP：完全平方 → <50 编码（显示 = 反查(√real)）；否则 ≥50 编码
            import math

            s = math.isqrt(real_value)
            if s * s == real_value:
                for v, r in enc.items():
                    if r == s:
                        return v
            for v, r in enc.items():
                if r == real_value:
                    return 50 + v
            raise ValueError(f"距离积 {real_value} 不在置换表映射中（{enc}）")
        if self.offset:
            # 2E1L：真实值 == 置换[显示] ± 1（方向未知）
            for v, r in enc.items():
                if r == real_value - 1 or r == real_value + 1:
                    return v
            raise ValueError(f"误差真实值 {real_value} 无对应加密显示（{enc}）")
        for v, r in enc.items():
            if r == real_value:
                return v
        raise ValueError(f"真实值 {real_value} 不在置换表中（{enc}）")

    def apply(self, model, total, clue_var, puzzle=None, row=None, col=None) -> Any:
        # clue_var 是固定值变量（lo == hi == 显示值）
        vid = clue_var.terms[0][0]
        v = model.vars[vid].lo
        if self.square:
            # 2EP 由 A2Product.encode 特判（平方需逐行绑定），这里不应走到
            raise AssertionError("RelationEncrypted(square) 的 apply 应由 A2Product 特判处理")
        perm = model.extras.get("perm")
        if perm is not None:
            target = perm[v]
        else:
            # 验证模式：置换表固定（副板答案已知）
            if puzzle is None:
                raise ValueError("RelationEncrypted.apply 需要 puzzle 或 model.extras['perm']")
            enc = permutation_from_puzzle(puzzle)
            target = Lin((), enc[v])
        if self.offset:
            # 2E1L：真实值 == 置换[显示] ± 1（双向）
            return Or(
                (
                    Cmp("==", total, target - Lin((), 1)),
                    Cmp("==", total, target + Lin((), 1)),
                )
            )
        return Cmp("==", total, target)
