"""WDyeDiff：染色雷 +1、非染色雷 -1（[N] Negative）。"""

from .weight import Weight


class WDyeDiff(Weight):
    id = "dye_diff"

    def coeff(self, cell) -> int:
        return 1 if cell.colored else -1
