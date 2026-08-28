"""用 legacy 脚本的输出交叉验证 mv1 规则求值器。

基准文件 `D:\\dev\\mv\\legacy\\stat\\mvpuzzle\\*.txt` 每关三行：

    :[V]5x5-10-10065 2 3          ← :关卡id 最大线索数 工作量
    foOoqfqfoOfoofOffOffqqofO     ← 原始 board（答案盘）
    f v3 V1 v1 q f q f v2 V1 ...  ← legacy 计算的「规则+值+可见性」

第三行是严格基准：本测试用我们的求值器从 board 重算，逐格比对。
"""

from __future__ import annotations

import glob
import os
import sys
from collections import Counter

sys.path.insert(0, "src")

from mv_dsl.puzzle.importer_mv1 import import_puzzle
from mv_dsl.rules.evaluator import clue_value

LEGACY_DIR = r"D:\dev\mv\legacy\stat\mvpuzzle"

# legacy short 形式 → 我们内部的规则 id（clue_dict2 映射）
SHORT_TO_RULE = {
    "v": "V", "m": "M", "l": "L", "w": "W", "n": "N", "x": "X",
    "p": "P", "e": "E", "x'": "X'", "k": "K", "w'": "W'", "e'": "E'",
    "lm": "LM", "mx": "MX", "nx": "NX", "mn": "MN",
}


def parse_legacy_block(lines: list[str], idx: int):
    """解析一个 legacy 关卡块，返回 (关卡原始行, 答案盘, short 列表)。"""
    header = lines[idx]  # :[V]5x5-10-10065 2 3
    board = lines[idx + 1]
    short = lines[idx + 2].split(" ")
    return header, board, short


def main(limit_per_file: int | None = None) -> int:
    files = sorted(glob.glob(os.path.join(LEGACY_DIR, "*.txt")))
    if not files:
        print(f"未找到基准文件: {LEGACY_DIR}")
        return 1

    total = matched = mismatched = skipped = 0
    by_rule: Counter[str] = Counter()
    bad_rule: Counter[str] = Counter()
    examples: list[str] = []

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f if ln.strip()]

        i = 0
        checked = 0
        while i + 2 < len(lines):
            if not lines[i].startswith(":"):
                i += 1
                continue
            header, board, short = parse_legacy_block(lines, i)
            i += 3
            if limit_per_file and checked >= limit_per_file:
                break

            level_id = header[1:].split(" ")[0]
            try:
                puzzle = import_puzzle(f"{level_id}\t{board}\tV;1x1")
            except Exception as exc:  # noqa: BLE001
                skipped += 1
                examples.append(f"导入失败 {level_id}: {exc}")
                continue

            # legacy 的 board 字符串与关卡 id 需尺寸一致
            if len(short) != puzzle.width * puzzle.height:
                skipped += 1
                continue

            checked += 1
            for pos, token in enumerate(short):
                r, c = divmod(pos, puzzle.width)
                token_low = token.lower()

                if token_low in ("f", "q", "qprior"):
                    continue  # 雷 / 空，无线索值
                # 拆分为「规则前缀 + 数值」
                if token_low.endswith("`"):
                    continue  # 渲染用的可见标记，不应出现在此行
                idx = 0
                while idx < len(token_low) and not token_low[idx].isdigit() and token_low[idx] != "-":
                    idx += 1
                rule_short = token_low[:idx]
                raw_value = token_low[idx:]
                if rule_short not in SHORT_TO_RULE:
                    skipped += 1
                    continue

                rule = SHORT_TO_RULE[rule_short]
                # Liar 的方向信息在 legacy short 中丢失（G/L 都映射为 L）→ 跳过
                if rule == "L":
                    skipped += 1
                    continue

                cell = puzzle.cells[r][c]
                if cell.clue is None:
                    skipped += 1
                    continue

                # 用我们的求值器重算（规则 id 取自导入结果，含 Liar 方向）
                try:
                    ours = clue_value(puzzle, r, c, cell.clue.rule)
                except Exception as exc:  # noqa: BLE001
                    skipped += 1
                    examples.append(f"求值失败 {level_id} {rule}: {exc}")
                    continue

                # legacy 的期望值
                if rule == "W":
                    expected: int | tuple[int, ...] = tuple(
                        int(ch) for ch in raw_value
                    ) if raw_value else ()
                elif rule == "E'":
                    # legacy 用箭头表示方向，数值取绝对值
                    expected = int("".join(ch for ch in raw_value if ch.isdigit()) or 0)
                    ours = abs(ours) if isinstance(ours, int) else ours
                else:
                    expected = int(raw_value) if raw_value else 0

                total += 1
                by_rule[rule] += 1
                if ours == expected:
                    matched += 1
                else:
                    mismatched += 1
                    bad_rule[rule] += 1
                    # 每条规则各留 3 个样例，便于定位
                    per_rule = sum(
                        1 for e in examples if e.startswith(f"[{rule}]")
                    )
                    if per_rule < 3:
                        examples.append(
                            f"[{rule}] {level_id} ({r},{c}) 内核={ours} legacy={expected}"
                        )

    print(f"比对格子数: {total}  一致: {matched}  不一致: {mismatched}  跳过: {skipped}")
    print(f"一致率: {matched / total * 100:.2f}%" if total else "无数据")
    print("\n各规则比对数（前 15）:")
    for rule, n in by_rule.most_common(15):
        bad = bad_rule.get(rule, 0)
        flag = "" if bad == 0 else f"  ← 不一致 {bad}"
        print(f"  {rule:4} {n:6}{flag}")
    if examples:
        print("\n样例差异/异常:")
        for e in examples[:10]:
            print(f"  {e}")
    return 0 if mismatched == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
