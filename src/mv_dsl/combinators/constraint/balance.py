"""CBalance：平衡（[1B]）——每行每列的雷数相等。

官方要求每行 == 每列 == MineCount / SizeX（需整除）。
对照官方 BuildMetaConstraints case "[1B]"（mv2 反编译 2382-2425 行）。
"""

from __future__ import annotations

from ...ir.expr import Cmp, Lin, all_of, sum_of
from .constraint import Constraint


class CBalance(Constraint):
    id = "B"

    def encode(self, model, puzzle, mine_vars):
        n = puzzle.height
        if puzzle.mine_count is None or puzzle.mine_count % n != 0:
            raise ValueError("[1B] Balance 要求雷数能被边长整除")
        per = puzzle.mine_count // n
        clauses = []
        for r in range(n):
            clauses.append(
                Cmp("==", sum_of(Lin(((mine_vars[(r, c)], 1),)) for c in range(n)), Lin((), per))
            )
        for c in range(n):
            clauses.append(
                Cmp("==", sum_of(Lin(((mine_vars[(r, c)], 1),)) for r in range(n)), Lin((), per))
            )
        return all_of(clauses)
