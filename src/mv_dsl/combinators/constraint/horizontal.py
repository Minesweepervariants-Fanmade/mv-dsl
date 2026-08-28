"""GHorizontal：横向（[1H]）——所有雷不能与其他雷横向相邻。"""

from __future__ import annotations

from ...ir.expr import BVar, Not, Or, all_of
from .constraint import Constraint


class CHorizontal(Constraint):
    id = "H"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width - 1):
                clauses.append(
                    Or(
                        (
                            Not(BVar(mine_vars[(r, c)])),
                            Not(BVar(mine_vars[(r, c + 1)])),
                        )
                    )
                )
        return all_of(clauses)
