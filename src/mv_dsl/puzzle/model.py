"""统一谜题模型（L3）。

两代官方文件格式不同，但都编码了同一件东西：**答案盘 + 规则集 + 每格线索**。
本模块把它们统一为 `Puzzle`，供编译器与验证器消费。

坐标约定统一为 `cells[row][col]`（与官方反编译源码的 (i, j) 一致）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True, slots=True)
class Clue:
    """一个格子上的线索。

    Attributes:
        rule: 规则 ID，如 "V"、"1L"、"2A"；组合规则形如 "2EL"（Encrypted ∘ Liar）。
        value: 显示值。官方 mv2 直接给出；mv1 需从答案盘计算（`None` 表示待计算）。
            多值线索（如数墙 [1W] 的 "123"）用 int 元组表示。
        visible: 初始是否对玩家可见（官方用字母大小写编码）。
    """

    rule: str
    value: int | tuple[int, ...] | None = None
    visible: bool = True


@dataclass(frozen=True, slots=True)
class Cell:
    """一个格子。多角色设计——**不预设「雷 xor 线索」**，这是雷线索（未来规则）的基础。"""

    mine: bool = False
    clue: Clue | None = None
    colored: bool = False


@dataclass(frozen=True, slots=True)
class Sideboard:
    """副板（sideboard）。

    官方把副板布局藏在 `[&&]` 与仲裁属性里隐式推导，这里改为**显式声明**。
    `cells` 保留原始 token，语义由对应规则解释。
    """

    kind: str  # permutation | error_marks | direction_mask | column_counts
    width: int
    height: int
    cells: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class Puzzle:
    source: str  # "mv1" | "mv2"
    level_id: str
    rules: tuple[str, ...]
    width: int
    height: int
    cells: tuple[tuple[Cell, ...], ...]
    mine_count: int | None = None
    sideboard: Sideboard | None = None

    @property
    def size(self) -> tuple[int, int]:
        return (self.height, self.width)

    def cell(self, row: int, col: int) -> Cell:
        return self.cells[row][col]

    def iter_cells(self) -> Iterator[tuple[int, int, Cell]]:
        for r, row in enumerate(self.cells):
            for c, cell in enumerate(row):
                yield r, c, cell

    def answer_mines(self) -> frozenset[tuple[int, int]]:
        """答案盘中的雷位置——这是验证正确性的基准。"""
        return frozenset(
            (r, c) for r, c, cell in self.iter_cells() if cell.mine
        )

    def has_rule(self, rule: str) -> bool:
        return rule in self.rules
