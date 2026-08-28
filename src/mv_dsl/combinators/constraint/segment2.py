"""GSegment：分段（[2S]）——每行有且仅有一组连续的雷。

行内段起点计数 == 1：起点 = b[c] ∧ ¬b[c-1]（行首 b[0] 自身即起点，因左边界恒非雷）。
"""

from __future__ import annotations

from ...ir.expr import BVar, Cmp, Lin, Iff, And, Not, all_of, sum_of
from .constraint import Constraint


class C2Segment(Constraint):
    id = "2S"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            starts = []
            for c in range(puzzle.width):
                b = BVar(mine_vars[(r, c)])
                if c == 0:
                    start = b  # 行首：左边界恒非雷
                else:
                    start = And((b, Not(BVar(mine_vars[(r, c - 1)]))))
                aux = model.new_bool(f"segstart_row{r}_c{c}")
                model.add(Iff(aux, start))
                starts.append(Lin(((aux.vid, 1),)))
            clauses.append(Cmp("==", sum_of(starts), Lin((), 1)))
        return all_of(clauses)
