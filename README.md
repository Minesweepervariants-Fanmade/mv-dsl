# mv-dsl

Declarative rule DSL and CP-SAT solver for **14 Minesweeper Variants** (1 & 2).

覆盖官方两代游戏的全部规则，支持规则组合（如 `2E&`、`2L&`）与未来扩展（如雷线索）。

## 设计要点

- **声明式外壳**：谜题是数据（board / rules / grid / sideboards / cell 多角色）
- **函数式内核**：规则是组合子的组合，约束由编译器生成
- **六类组合子**：`Region` / `Weight` / `Aggregate` / `Relation` / `Global` / `Sideboard`
- **统一管道**：$\text{clue} = \mathrm{Relation}(\mathrm{Aggregate}(\mathrm{Weight}(\mathrm{Region}(i,j))))$
- **组合规则 = 管道复合**，不为任何组合写专门代码
- **后端无关 IR**：CP-SAT 为主后端，Z3 / csugar 可选

架构与完整计划见 [PROJECT.md](./PROJECT.md)。

## 状态

| 阶段 | 内容 | 状态 |
|---|---|---|
| 一 | IR + CP-SAT 后端 + mv1 规则 | 进行中 |
| 二 | 全局与副板 + 官方格式导入器 | 进行中 |
| 三 | 组合与 mv2 规则 | 待开始 |
| 四 | 唯一性验证 / 全解枚举 / 难度评估 | 待开始（难度评估非优先） |

## 开发

```powershell
uv sync
uv run pytest
```

## 许可证

Apache-2.0

> 参考了 Minesweepervariants-Fanmade 项目的**算法思路**（no-good 唯一性验证、clone + AddHint 增量补偿等），
> 但该项目为 GPL-3.0，本项目未复用其任何代码。
