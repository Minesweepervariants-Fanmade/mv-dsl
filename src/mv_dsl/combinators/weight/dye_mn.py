"""WDyeMn：染色雷 +2、非染色雷 -1（[M][N] Multiple∘Negative）。"""

from .weight import Weight


class WDyeMn(Weight):
    id = "dye_mn"

    def coeff(self, cell) -> int:
        return 2 if cell.colored else -1
