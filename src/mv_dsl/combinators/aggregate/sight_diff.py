"""ASightDiff：纵横视野差（[E'] Eyesight'）。

值 = 纵向视野（上+下）− 横向视野（左+右），**带符号**——符号指示更长方向
（正=纵向更长 ↕，负=横向更长 ↔），与官方实现一致。
"""

from __future__ import annotations

from .eyesight import _direction_groups, vision_chain
from .aggregate import Aggregate


class ASightDiff(Aggregate):
    id = "sight_diff"

    def value(self, puzzle, row, col, cells, weight):
        r0, c0 = row, col
        vertical = 0
        for dr in (-1, 1):
            r = r0 + dr
            while 0 <= r < puzzle.height:
                if puzzle.cells[r][c0].mine:
                    break
                vertical += 1
                r += dr
        horizontal = 0
        for dc in (-1, 1):
            c = c0 + dc
            while 0 <= c < puzzle.width:
                if puzzle.cells[r0][c].mine:
                    break
                horizontal += 1
                c += dc
        return vertical - horizontal

    def encode(self, model, puzzle, row, col, cells, weight, mine_vars, clue_var, relation):
        up, down, left, right = _direction_groups(puzzle, row, col, _region_of(puzzle, row, col))
        total = (
            vision_chain(model, up, mine_vars, "u")
            + vision_chain(model, down, mine_vars, "d")
            - (vision_chain(model, left, mine_vars, "l") + vision_chain(model, right, mine_vars, "r"))
        )
        return relation.apply(model, total, clue_var, puzzle, row, col)


def _region_of(puzzle, row, col):
    from ..region.eyesight import REyesight

    return REyesight()
