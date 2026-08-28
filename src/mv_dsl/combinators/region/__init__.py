"""Region（区域）组合子：$(i,j) \\to$ 格子集合。"""

from .region import Region
from .std import Rstd
from .knight import RKnight
from .cross import RCross
from .mini_cross import RMiniCross
from .eyesight import REyesight
from .shift_up import RShiftUp
from .shift_up_two import RShiftUpTwo
from .full import RFull

__all__ = ["Region", "Rstd", "RKnight", "RCross", "RMiniCross", "REyesight", "RShiftUp", "RShiftUpTwo", "RFull"]
