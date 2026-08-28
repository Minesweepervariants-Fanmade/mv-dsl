"""14 Minesweeper Variants 1（mv1）官方谜题导入器。

文件格式（`puzzle/all_puzzles_dedup.txt`，TAB 分隔，首行为 `!!CLEARED`）：

    <level_id>\t<board>\t<difficulty>
    [C][T]7x7-20-10013\tqfofqoqfqffofffqqqfoqoqoqfqOfoffoooqfqqffqqqfo\t4x3,3x3,2x5,1x9,-1x1,-3x1

- `level_id`：`<MetaInfo><W>x<H>-<雷数>-<编号>`，MetaInfo 形如 `[C][T]`（可含 `!` 难度标记）
- `board`：**答案盘**，长 `W*H` 的紧凑字符串，每格一个字符
- `difficulty`：官方求解复杂度直方图（SolutionSummary），形如 `4x3,3x3,-1x1`

board 字符语义（**注意与 MetaInfo 的字母含义不同，这是 mv1 格式的坑**）：

| 字符 | 含义 |
|---|---|
| `f` | 雷（隐藏） |
| `q` | 非雷，无线索，隐藏 |
| `Q` | 非雷，无线索，可见 |
| 其他字母 | 线索格；**字母编码规则类型**，大写=初始可见、小写=初始隐藏 |

线索值**不在文件中**——需从答案盘按规则计算（见 `mv_dsl.rules.evaluator`）。
官方参考实现见 `D:\\dev\\mv\\legacy\\stat\\puzzle_mv.py` 的 `clue()`。
"""

from __future__ import annotations

import re

from .model import Cell, Clue, Puzzle

__all__ = [
    "parse_level_id",
    "parse_board",
    "import_puzzle",
    "import_file",
    "CLUE_LETTERS",
]

# level_id 中的 MetaInfo：`[C][T]7x7-20-10013` → ("C", "T")
# 规则 id 可含数字/字母/撇号/井号/加号/尖号，如 1T'、#'、R+
_RULE_PATTERN = re.compile(r"\[([\dA-Za-z'^#+]+?)\+?\]")
_SIZE_PATTERN = re.compile(r"(\d+)x(\d+)")

# board 字符 → 规则 id。
# 带 +/- 后缀者为误差规则（Liar）的方向：G=+1、L=-1（组合规则 LM 同理）。
CLUE_LETTERS: dict[str, str] = {
    "O": "V",    # Vanilla
    "M": "M",    # Multiple：染色格雷计 2
    "G": "L+",   # Liar +1
    "L": "L-",   # Liar -1
    "T": "W",    # Wall：各连续雷段长度
    "N": "N",    # Negative：染色与非染色雷数差
    "Z": "X",    # Cross：半径 2 十字
    "S": "P",    # Partition：连续雷组数
    "I": "E",    # Eyesight：四向可见非雷格数
    "Y": "X'",   # Mini Cross：半径 1 十字
    "X": "K",    # Knight：马步 8 格
    "R": "W'",   # Longest Wall：最长连续雷段
    "H": "E'",   # Eyesight'：纵横视野差 + 方向
    # 组合规则：同一字母随关卡类型改变含义（legacy 先替换再查表，此处直接查表等价）
    "D": "LM+",  # Liar(+1) ∘ Multiple
    "E": "LM-",  # Liar(-1) ∘ Multiple
    "B": "MX",   # Multiple ∘ Cross
    "C": "NX",   # Negative ∘ Cross
    "A": "MN",   # Multiple ∘ Negative
}

# 纯占位字符：非雷且无线索
_EMPTY_CHARS = frozenset("qQ")


def parse_level_id(level_id: str) -> tuple[tuple[str, ...], int, int, int | None]:
    """解析 level_id，返回 (规则元组, 宽, 高, 雷数)。

    `[C][T]7x7-20-10013` → `(("C", "T"), 7, 7, 20)`
    """
    rules = tuple(_RULE_PATTERN.findall(level_id.split("-")[0]))
    size = _SIZE_PATTERN.search(level_id)
    if size is None:
        raise ValueError(f"无法解析尺寸: {level_id!r}")
    width, height = int(size.group(1)), int(size.group(2))

    mine_count: int | None = None
    parts = level_id.split("-")
    if len(parts) >= 3:
        try:
            mine_count = int(parts[1])
        except ValueError:
            mine_count = None
    return rules, width, height, mine_count


def parse_board(board: str, width: int, height: int) -> tuple[tuple[Cell, ...], ...]:
    """解析 mv1 答案盘字符串为格子矩阵。

    染色沿用官方规则：`(row + col) % 2 == 1`（1M / 1N 依赖）。
    """
    flat = board.replace(" ", "")
    expected = width * height
    if len(flat) != expected:
        raise ValueError(
            f"board 长度 {len(flat)} 与尺寸 {width}x{height} 不符（期望 {expected}）"
        )

    cells: list[tuple[Cell, ...]] = []
    for r in range(height):
        row: list[Cell] = []
        for c in range(width):
            ch = flat[r * width + c]
            colored = (r + c) % 2 == 1

            if ch in ("f", "F"):
                row.append(Cell(mine=True, colored=colored))
            elif ch in _EMPTY_CHARS:
                row.append(Cell(mine=False, colored=colored))
            else:
                rule = CLUE_LETTERS.get(ch.upper())
                if rule is None:
                    raise ValueError(f"未知 board 字符: {ch!r}")
                row.append(
                    Cell(
                        mine=False,
                        clue=Clue(rule=rule, value=None, visible=ch.isupper()),
                        colored=colored,
                    )
                )
        cells.append(tuple(row))
    return tuple(cells)


def import_puzzle(line: str) -> Puzzle:
    """导入单行谜题记录。"""
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 2:
        raise ValueError(f"字段不足: {line[:80]!r}")
    level_id, board = parts[0], parts[1]

    rules, width, height, mine_count = parse_level_id(level_id)
    cells = parse_board(board, width, height)
    return Puzzle(
        source="mv1",
        level_id=level_id,
        rules=rules,
        width=width,
        height=height,
        cells=cells,
        mine_count=mine_count,
    )


def import_file(path: str, limit: int | None = None) -> list[Puzzle]:
    """导入整个关卡文件。首行 `!!CLEARED` 会被跳过。"""
    puzzles: list[Puzzle] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f):
            if lineno == 0 and line.startswith("!!"):
                continue
            if not line.strip():
                continue
            puzzles.append(import_puzzle(line))
            if limit is not None and len(puzzles) >= limit:
                break
    return puzzles
