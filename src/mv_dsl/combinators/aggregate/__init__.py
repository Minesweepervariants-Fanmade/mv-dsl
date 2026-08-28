"""Aggregate（聚合）组合子：格子集合 → 数值。"""

from .aggregate import Aggregate, wall_segments_from
from .sum import ASum
from .absolute_sum import AAbsoluteSum
from .wall_segments import AWallSegments
from .longest_wall import ALongestWall
from .group_count import AGroupCount
from .eyesight import AEyesight
from .sight_diff import ASightDiff
from .cross2 import A2Cross
from .cross_either2 import A2CrossEither
from .product2 import A2Product
from .area2 import A2Area

__all__ = [
    "Aggregate",
    "wall_segments_from",
    "ASum",
    "AAbsoluteSum",
    "AWallSegments",
    "ALongestWall",
    "AGroupCount",
    "AEyesight",
    "ASightDiff",
    "A2Cross",
    "A2CrossEither",
    "A2Product",
    "A2Area",
]
