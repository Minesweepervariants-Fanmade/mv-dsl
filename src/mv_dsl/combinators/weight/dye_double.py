"""WDyeDouble：染色格雷计 2、非染色计 1（[M] Multiple）。"""

from .weight import Weight


class WDyeDouble(Weight):
    id = "dye_double"

    def coeff(self, cell) -> int:
        return 2 if cell.colored else 1
