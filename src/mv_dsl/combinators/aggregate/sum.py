"""ASum：加权求和（[V]/[M]/[X]/[K] 等线性类规则的聚合）。"""

from __future__ import annotations

from ...ir.expr import Lin, sum_of
from .aggregate import Aggregate


class ASum(Aggregate):
    id = "sum"

    def value(self, puzzle, row, col, cells, weight):
        total = 0
        for r, c in cells:
            if puzzle.cells[r][c].mine:
                total += weight.coeff(puzzle.cells[r][c])
        return total

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        terms = [
            Lin(((mine_vars[(r, c)], weight.coeff(puzzle.cells[r][c])),))
            for r, c in cells
        ]
        total = sum_of(terms)
        return relation.apply(model, total, clue_var)
