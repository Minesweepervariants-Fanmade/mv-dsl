"""L2 六类组合子：抽象基类 + 具体子类（每子类独立文件）。

六类组合子构成规则的语义空间：

| 类别 | 抽象基类 | 文件 | 职责 |
|---|---|---|---|
| Region | `Region` | `region.py` | $(i,j) \\to$ 格子集合 |
| Weight | `Weight` | `weight.py` | 每颗雷计入多少 |
| Aggregate | `Aggregate` | `aggregate.py` | 集合 $\\to$ 数值 |
| Relation | `Relation` | `relation.py` | 真实值 $\\leftrightarrow$ 显示值 |
| Global | `Constraint` | `constraint.py` | 整盘布局约束（全局规则） |
| Sideboard | `Sideboard` | `sideboard.py` | 副板模式（额外变量 + 布局） |

一条线索规则 = `ClueRule`（`rule.py`）管道实例：

$$\\text{clue} = \\mathrm{Relation}(\\mathrm{Aggregate}(\\mathrm{Weight}(\\mathrm{Region}(i,j))))$$

求值器与编译器只依赖管道的 `value()` / `encode()` 两个方法，
保证 fill 与约束生成语义一致。
"""
