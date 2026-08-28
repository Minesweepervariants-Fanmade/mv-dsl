"""GAntiKnight：无马步（[1A]）——所有雷的马步位置不能有雷。"""

from __future__ import annotations

from ...ir.expr import BVar, Not, Or, all_of
from .constraint import Constraint

_KNIGHT = (
    (1, 2), (2, 1), (1, -2), (2, -1), (-1, 2), (-2, 1), (-1, -2), (-2, -1),
)


class CAntiKnight(Constraint):
    id = "A"

    def encode(self, model, puzzle, mine_vars):
        clauses = []
        for r in range(puzzle.height):
            for c in range(puzzle.width):
                for dr, dc in _KNIGHT:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < puzzle.height and 0 <= nc < puzzle.width:
                        clauses.append(
                            Or((Not(BVar(mine_vars[(r, c)])), Not(BVar(mine_vars[(nr, nc)]))))
                        )
        return all_of(clauses)
