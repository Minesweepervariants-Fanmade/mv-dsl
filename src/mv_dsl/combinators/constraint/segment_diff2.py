"""C2SegmentDiff：分段'（[2S']）——同一行中任意两段连续雷长度不同。

对照官方 BuildMetaConstraints case "[2S']"（mv2 反编译 2697-2720 行）：
对每行、每对长度相同的两段（不重叠，间隔 ≥2），禁止「两段同时完整存在」。
段完整 = 段内全雷 ∧ 段外相邻格非雷。
"""

from __future__ import annotations

from ...ir.expr import And, BVar, Cmp, Lin, Not, Or, all_of
from .constraint import Constraint


class C2SegmentDiff(Constraint):
    id = "2S'"

    def encode(self, model, puzzle, mine_vars):
        h, w = puzzle.height, puzzle.width
        clauses = []

        def seg_full(row: int, s: int, e: int):
            """段 [s, e] 完整存在：段内全雷 ∧ 段外相邻格非雷。"""
            terms = [BVar(mine_vars[(row, k)]) for k in range(s, e + 1)]
            if s > 0:
                terms.append(Not(BVar(mine_vars[(row, s - 1)])))
            if e + 1 < w:
                terms.append(Not(BVar(mine_vars[(row, e + 1)])))
            return And(tuple(terms))

        for r in range(h):
            for s1 in range(w):
                for e1 in range(s1, w):
                    # 第二段起点 ≥ 第一段终点 + 2（不重叠、间隔 ≥1 非雷）
                    for s2 in range(e1 + 2, w):
                        length = e1 - s1 + 1
                        e2 = s2 + length - 1
                        if e2 >= w:
                            break
                        # 禁止两等长段共存
                        clauses.append(
                            Or((Not(seg_full(r, s1, e1)), Not(seg_full(r, s2, e2))))
                        )

        return all_of(clauses)
