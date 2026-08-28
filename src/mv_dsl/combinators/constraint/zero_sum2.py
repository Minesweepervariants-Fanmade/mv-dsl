"""GZeroSum：零和（[2Z]）——每行的染色格与非染色格的雷数相等。"""

from __future__ import annotations

from ...ir.expr import Cmp, Lin, all_of, sum_of
from .constraint import Constraint


class C2ZeroSum(Constraint):
    id = "2Z"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            colored = []
            uncolored = []
            for c in range(puzzle.width):
                vid = mine_vars[(r, c)]
                if puzzle.cells[r][c].colored:
                    colored.append(Lin(((vid, 1),)))
                else:
                    uncolored.append(Lin(((vid, 1),)))
            clauses.append(Cmp("==", sum_of(colored), sum_of(uncolored)))
        return all_of(clauses)
