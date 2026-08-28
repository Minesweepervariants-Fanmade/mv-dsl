"""WIdentity：每颗雷计 1（[V] 及多数规则）。"""

from .weight import Weight


class WIdentity(Weight):
    id = "identity"

    def coeff(self, cell) -> int:
        return 1
