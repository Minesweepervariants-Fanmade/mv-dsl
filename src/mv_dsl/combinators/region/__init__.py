"""Region（区域）组合子：$(i,j) \\to$ 格子集合。"""

from .region import Region
from .moore import RMoore
from .knight import RKnight
from .cross import RCross
from .mini_cross import RMiniCross
from .eyesight import REyesight

__all__ = ["Region", "RMoore", "RKnight", "RCross", "RMiniCross", "REyesight"]
