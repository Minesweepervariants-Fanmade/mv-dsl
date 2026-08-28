"""Constraint（全局谓词）组合子。"""

from .constraint import Constraint
from .quad import CQuad
from .triplet import CTriplet
from .balance import CBalance
from .unary import CUnary
from .anti_knight import CAntiKnight
from .horizontal import CHorizontal
from .dual import CDual
from .horizontal2 import C2Horizontal
from .triplet2 import C2Triplet
from .zero_sum2 import C2ZeroSum
from .flower2 import C2Flower
from .triplet_req import CTripletReq
from .connected import CConnected
from .group2 import C2Group4, C2Group3
from .segment2 import C2Segment
from .outside import COutside
from .snake import CSnake
from .connected2 import C2Connected
from .bridge2 import C2Bridge
from .bridge_diag2 import C2BridgeDiag
from .segment_diff2 import C2SegmentDiff
from .battleship import CBattleship

__all__ = [
    "Constraint",
    "CQuad", "CTriplet", "CBalance", "CUnary", "CAntiKnight",
    "CHorizontal", "CDual", "C2Horizontal", "C2Triplet", "C2ZeroSum", "C2Flower",
    "CTripletReq", "CConnected",
    "C2Group4", "C2Group3", "C2Segment",
    "COutside", "CSnake", "C2Connected", "C2Bridge", "C2BridgeDiag", "C2SegmentDiff",
    "CBattleship",
]
