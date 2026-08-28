"""14 Minesweeper Variants 2（mv2）官方谜题导入器。

文件格式（`puzzle/all_puzzles_dedup.txt`，TAB 分隔，首行 `!!CLEARED`）：

    <level_id>\t<board>
    [1B][2A]!5x5-10-(4x2,3x1,2x1,1x4;L4R4)-1636\tf 2A1 q f q q 2A6 f f 2a4 ...

- `level_id`：`<MetaInfo><!难度><W>x<H>-<雷数>-(<求解复杂度>;L?R?)-<编号>`
- `board`：**答案盘 + 副板**，空格分隔的 token 序列

与 mv1 的两个关键差异（本模块的核心）：

1. **线索值直接标注在 token 里**（mv1 需从答案盘计算）：`2A1` = 规则 2A、值 1
2. **误差线索（Liar）编码不同**：token 带 `-` 后缀的数字表示「真实值 = 显示值 - 1」，
   例如 `2l-4` → 显示 4、真实 3；`2L-3` → 显示 3、真实 2。
   官方参考实现见 `D:\\dev\\mv\\legacy\\stat\\puzzle_mv2.py` 的 `parse()`。

token 语义：

| token | 含义 |
|---|---|
| `f` / `F` | 雷（小写=隐藏，大写=初始可见） |
| `q` / `Q` | 非雷无线索（小写=隐藏，大写=可见） |
| `qprior` | 非雷无线索，优先级标记 |
| `FX` / `QX` | 副板专用占位（2E^ / 2P 等） |
| `V3` / `v3` | 规则 id + 值（**大写=初始可见，小写=隐藏**） |
| `2A1` / `2a1` | 同上，规则 id 以数字开头 |
| `2EL2` / `2el-2` | 组合规则 token（Encrypted ∘ Liar） |
| `v-7` | 负值线索（V 值 7 的特殊写法，出现于 2B/2I 关卡） |

副板：当 `col > row` 时，board 尾部含副板区域（宽 `col - row`），
按 `[主板(row × row) | 副板(row × (col-row))]` 逐行交错排列（见 legacy `Puzzle.__init__`）。
"""

from __future__ import annotations

import re

from .model import Cell, Clue, Puzzle, Sideboard

__all__ = ["parse_level_id", "parse_token", "import_puzzle", "import_file"]

# MetaInfo：`[1B][2A]!5x5` → ("1B", "2A")；规则 id 形如 1T'、2X'、2E^、#'、R+
_RULE_PATTERN = re.compile(r"\[([\dA-Za-z'^#+]+?)\+?\]")
_SIZE_PATTERN = re.compile(r"(\d+)x(\d+)")

# 纯占位 token（非雷、无线索）
_EMPTY_TOKENS = {"q": False, "Q": True, "qprior": True}
# 副板占位：QX 非雷；FX 是**可见雷**（副板 2P 距离积表列等，官方 "F" 开头 = 雷）
_SIDE_MINE = {"FX"}
_SIDE_EMPTY = {"QX"}
# 明确的雷 token
_MINE_TOKENS = {"f", "F"}

# 副板类型推断：规则 → 副板语义
_SIDEBOARD_KIND: dict[str, str] = {
    "2E": "permutation",     # 加密：字母 ↔ 数字置换矩阵
    "2E^": "permutation",    # 加密^：双表置换
    "2L": "error_marks",     # 误差：每行每列的误差标记
    "2L'": "error_marks",
    "2I": "direction_mask",  # 残缺：被剔除方向掩码
    "2U": "column_counts",   # 失衡：列计数
}


def parse_level_id(level_id: str) -> tuple[tuple[str, ...], int, int, int | None]:
    """解析 level_id，返回 (规则元组, 主板边长, 总列数, 雷数)。

    `[1B][2A]!5x10-10-(4x2,...)-1608` → `(("1B", "2A"), 5, 10, 10)`

    **坐标语义（易错）**：官方写作 `<主板边长>x<总列数>`，而非 `宽x高`。
    主板恒为 `边长 × 边长` 方阵；当总列数大于边长时，差值即副板宽度。
    对照官方参考实现 `puzzle_mv2.py`：其 `row` 即主板边长、`col` 即总列数。
    """
    head = level_id.split("-")[0]
    rules = tuple(_RULE_PATTERN.findall(head))
    size = _SIZE_PATTERN.search(level_id)
    if size is None:
        raise ValueError(f"无法解析尺寸: {level_id!r}")
    board_size, total_width = int(size.group(1)), int(size.group(2))

    mine_count: int | None = None
    parts = level_id.split("-")
    if len(parts) >= 3:
        try:
            mine_count = int(parts[1])
        except ValueError:
            mine_count = None
    return rules, board_size, total_width, mine_count


def parse_token(token: str) -> tuple[bool, Clue | None, bool]:
    """解析单个格子 token，返回 (是否雷, 线索, 是否可见)。

    规则 id 与数值的切分规则：token 形如 `<规则id><值>`，其中规则 id 由
    数字/字母/撇号/尖号组成，值为剩余部分（可含前导 `-`）。
    """
    if token in _MINE_TOKENS:
        return True, None, token.isupper()
    if token in _EMPTY_TOKENS:
        return False, None, _EMPTY_TOKENS[token]
    if token in _SIDE_MINE:
        return True, None, True  # 副板可见雷（FX）
    if token in _SIDE_EMPTY:
        return False, None, True  # 副板非雷占位（QX）

    visible = any(ch.isupper() for ch in token)
    low = token.lower()

    # 特殊写法：v-7 → 规则 V、值 7（legacy parse 直接返回 '7'）
    if low.startswith("v-") and low[2:].isdigit():
        return False, Clue(rule="V", value=int(low[2:]), visible=visible), visible

    # 切分规则 id 与数值：从最长匹配处断开
    m = re.match(r"([0-9a-z'^]+?)(-?\d+|-\d+)$", low)
    if m is None:
        raise ValueError(f"无法解析 token: {token!r}")
    rule_raw, value_raw = m.group(1), m.group(2)

    # 规则 id 还原大小写形态（2X' 等）：保留撇号/尖号
    rule = _restore_rule_case(rule_raw, token)
    value = int(value_raw)

    # [2L] 误差归一化：带 `-` 的 token 是**误差格**（玩家不知道 +1/-1），
    # 规则 id 加 `-` 后缀标记（"2L-" / "2LM-" / "2EL-"），注册表据此选
    # RelationOffset（双向 ±1）而非 RelationEquals。
    # 值编码分两种（对照官方 GetCellConstraint）：
    # - 一般组合（2L/2LM/2LD/2LX/2LA/2L1x）：num77 = -neg - 1（显示值）
    # - [2LP]（距离积，官方 :4313 num92 = |value|）：保持绝对值原样——
    #   完全平方时真实距离积 ∈ {(√|v|-1)², (√|v|+1)²}，否则 == |v|
    if value_raw.startswith("-") and (rule.startswith("2L") or rule == "2EL"):
        if rule == "2LP":
            value = -value
        else:
            value = -value - 1
        rule = rule + "-"
    return False, Clue(rule=rule, value=value, visible=visible), visible


def _restore_rule_case(rule_raw: str, original: str) -> str:
    """按原始 token 的大小写形态还原规则 id（如 `2x'` → `2X'`）。"""
    rule = rule_raw.upper()
    # 撇号/尖号一律保留；其余按官方命名规范大写
    return rule


def _split_sideboard(
    tokens: list[str], board_size: int, total_width: int
) -> tuple[list[str], list[str] | None, int]:
    """按官方布局切分主板与副板。

    当 `total_width > board_size` 时，board 逐行排列为
    `[主板 board_size 格 | 副板 (total_width - board_size) 格]`，共 board_size 行。
    """
    if total_width <= board_size:
        return tokens, None, 0
    side_w = total_width - board_size
    main: list[str] = []
    side: list[str] = []
    for r in range(board_size):
        row = tokens[r * total_width : (r + 1) * total_width]
        main.extend(row[:board_size])
        side.extend(row[board_size:])
    return main, side, side_w


def _infer_sideboard_kind(rules: tuple[str, ...]) -> str:
    for rule in rules:
        if rule in _SIDEBOARD_KIND:
            return _SIDEBOARD_KIND[rule]
    return "unknown"


def import_puzzle(line: str) -> Puzzle:
    """导入单行谜题记录。"""
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 2:
        raise ValueError(f"字段不足: {line[:80]!r}")
    level_id, board = parts[0], parts[1]

    rules, board_size, total_width, mine_count = parse_level_id(level_id)
    tokens = board.strip().split(" ")
    main_tokens, side_tokens, side_w = _split_sideboard(tokens, board_size, total_width)

    expected = board_size * board_size
    if len(main_tokens) != expected:
        raise ValueError(
            f"主板 token 数 {len(main_tokens)} 与 {board_size}x{board_size} 不符（期望 {expected}）"
        )

    cells: list[tuple[Cell, ...]] = []
    for r in range(board_size):
        row: list[Cell] = []
        for c in range(board_size):
            token = main_tokens[r * board_size + c]
            mine, clue, _ = parse_token(token)
            row.append(Cell(mine=mine, clue=clue, colored=(r + c) % 2 == 1))
        cells.append(tuple(row))

    sideboard: Sideboard | None = None
    if side_tokens is not None and side_w > 0:
        side_cells = tuple(
            tuple(side_tokens[r * side_w : (r + 1) * side_w])
            for r in range(board_size)
        )
        sideboard = Sideboard(
            kind=_infer_sideboard_kind(rules),
            width=side_w,
            height=board_size,
            cells=side_cells,
        )

    return Puzzle(
        source="mv2",
        level_id=level_id,
        rules=rules,
        width=board_size,  # 求解只针对主板方阵
        height=board_size,
        cells=tuple(cells),
        mine_count=mine_count,
        sideboard=sideboard,
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
