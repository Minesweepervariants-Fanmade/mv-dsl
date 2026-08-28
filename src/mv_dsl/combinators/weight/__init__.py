"""Weight（权重）组合子：每颗雷计入多少。"""

from .weight import Weight
from .identity import WIdentity
from .dye_double import WDyeDouble
from .dye_diff import WDyeDiff
from .dye_mn import WDyeMn

__all__ = ["Weight", "WIdentity", "WDyeDouble", "WDyeDiff", "WDyeMn"]
