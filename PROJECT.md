# MVDSL 实现计划

> Minesweeper Variants DSL —— 覆盖 14 Minesweeper Variants 1/2 全部规则的声明式规则 DSL + CP-SAT 求解器
>
> 版本：v0.1（计划草案）　日期：2026-08-28　状态：待评审

---

## 目录

1. [项目总览](#1-项目总览)
2. [立项依据：现状分析](#2-立项依据现状分析)
3. [架构设计](#3-架构设计)
4. [DSL 规范](#4-dsl-规范)
5. [规则代数：六类组合子](#5-规则代数六类组合子)
6. [组合规则与可扩展性](#6-组合规则与可扩展性)
7. [后端选型](#7-后端选型)
8. [目录结构与模块划分](#8-目录结构与模块划分)
9. [Server 对接评估（MinesweeperVariants-Vue）](#9-server-对接评估minesweepervariants-vue)
10. [实施路线](#10-实施路线)
11. [验证策略](#11-验证策略)
12. [参考资料](#12-参考资料)
13. [风险与待定事项](#13-风险与待定事项)

---

## 1. 项目总览

### 1.1 目标

构建一套**声明式 DSL + CP-SAT 求解器**，完整覆盖《14 Minesweeper Variants》（14mv1）与《14 Minesweeper Variants 2》（14mv2）的全部规则，并满足三项硬性要求：

| 要求       | 说明                          | 达成手段                        |
| -------- | --------------------------- | --------------------------- |
| **全覆盖**  | 14mv1 + 14mv2 全部规则可表达       | 六类组合子（§5）穷尽规则语义空间           |
| **组合可靠** | 组合规则（如 `2E&`、`2L&`）无需特判即可工作 | 管道复合（§6），不为任何组合写专门代码        |
| **面向未来** | 雷线索（一个线索同时是雷）等新机制可扩展        | cell 多角色模型 + 后端无关 IR（§4、§7） |

### 1.2 非目标（v1 阶段）

- 不追求一次性覆盖 fanmade 社区的全部 369 个扩展规则（见 §2.2）——先覆盖官方 14mv1/2，再评估迁移
- 不做谜题生成/出题器（阶段五以后，见 §10）
- 不做图像渲染（fanmade 的 `image_template` 体系不在范围内）

### 1.3 项目定位

```
MVDSL = 规范化规则定义（DSL） + 高性能求解内核（CP-SAT） + 可选 server 适配层
```

独立于现有 fanmade 项目，从零构建，**不复用其代码**（许可证原因见 §13.1），但吸收其工程经验（§2.4）。

---

## 2. 立项依据：现状分析

### 2.1 官方游戏的隐式 DSL

反编译分析显示，官方游戏本身就是一套**隐式字符串 DSL**，但存在结构性缺陷：

| 层面   | 官方实现                                                        | 问题                                                   |
| ---- | ----------------------------------------------------------- | ---------------------------------------------------- |
| 规则标识 | `Symbols` 静态字符串常量，mv1 有 29 个 `RULE_*`，mv2 约 130 个           | 常量表爆炸，靠 `MetaInfo.Contains("[X]")` 分派                |
| 格子状态 | mv1 用 `char`；mv2 用 string token（`规则ID+数字后缀`，如 `2A6`、`2l-4`） | 编码语义与解析逻辑（mv2 的 `SeparateStringSuffixNumber`）耦合在解析器里 |
| 组合规则 | **预合成标识**：`2L1W`、`2E1M`、`GUESS_LIAR` 等各写专门 case             | 组合数 = 手写组合数，组合爆炸不可控                                  |
| 副板布局 | `[&&]` 分离副板 + `HasSeparateGuessLiarBoards` 等属性隐式仲裁          | 规则间的资源冲突靠隐式仲裁，不可预测                                   |

**结论**：官方实现的三段式结构（`GetSimpleClueAffectedRegion` 区域 → `GetClueAffectedRegion` 状态依赖区域 → `GetCellConstraint` 逐格约束）是**正确的领域抽象**，值得继承；但它的实现方式是字符串分派 + 预合成，不可扩展。MVDSL 要做的就是把这套抽象显式代数化。

### 2.2 fanmade 项目的规模与结构性障碍

本地拷贝 `D:\dev\mv\Minesweepervariants-Fanmade` 实测数据：

| 目录                     | 规则文件数   | 总行数         |
| ---------------------- | ------- | ----------- |
| `rule/Lrule`（布局规则）     | 192     | 18,536      |
| `rule/Rrule`（线索规则）     | 143     | 22,534      |
| `rule/Mrule`（线索-雷交互）   | 15      | 2,330       |
| `rule/sharpRule`（标签规则） | 18      | 2,164       |
| `rule/rule3D`          | 1       | 210         |
| **合计**                 | **369** | **≈45,774** |

最大单文件：`Rrule/1Eat.py`（905 行）、`Mrule/Masyu.py`（526 行）、`Rrule/2L2.py`（437 行）。

**核心障碍——组合规则不是复合而成，而是手工枚举。** 决定性证据在 `rule/Rrule/1L/` 目录：

```
1L/1L.py        134 行    ← 基础 Liar 规则
1L/1L1W.py      304 行    ← Liar + Wall
1L/1L1E'.py     277 行    ← Liar + Eyesight'
1L/1L2A.py      175 行    ← Liar + Area
1L/1L1P.py      151 行    ← Liar + Partition
1L/1L1X.py       93 行    ← Liar + Cross
1L/1L1M.py      106 行    ← Liar + Multiple
1L/1L2D.py       91 行    ← Liar + Deviation
1L/1L2M.py       89 行    ← Liar + Modulo
1L/1L1K.py       93 行    ← Liar + Knight
... 共 21 个文件，2,647 行
```

进一步验证继承关系：`1L1W.py:152` 的 `class Rule1L1W(AbstractClueRule)` 直接继承抽象基类，**与 `1L.py:29` 的 `Rule1L` 无任何代码复用**——每个组合都是复制粘贴后改写。同理 `rule/Rrule/2E/`（3 文件）、`1M1N1X`、`1N1X`、`1X2X` 等目录/文件皆为此模式。

这意味着：**N 个基础规则的两两组合，需要 O(N²) 个手写文件**。这是当前项目无法继续扩展的根本原因。

其他客观事实：

- **规则类职责过重**：以最简单的 `rule/Rrule/V.py`（119 行）为例，一个规则必须实现 6 类方法——`fill()`（生成线索值）、`from_json()`（反序列化）、`invalid()`（合法性）、`deduce_cells()`（手工单格推理）、`create_constraints()`（CP-SAT 约束）、`high_light()`（UI 高亮）。**求解逻辑、渲染逻辑、序列化逻辑、启发式推理逻辑混在同一个类里**。
- **约束写在 `AbstractValue` 上**：约束生成入口是 `AbstractValue.create_constraints(board, switch)`（见 `MinesweeperVariants/minesweepervariants/abs/rule.py:517`），即"值对象"负责约束，规则对象只负责填充。规则语义（区域/聚合/关系的定义）因此被分散到每个值对象内部，无法复用。
- **官方已承认需要组合特判**：`abs/rule.py:370` 定义了 `combine(rules)` 钩子，文档注释为"当多条规则同时生效时，单独逐条建立约束可能会导致效率低下……允许具体规则实现自行检查、判断是否存在可以进行联合优化的情况"。即组合优化被设计为**各规则自己特判**，而非架构统一处理。
- **元信息靠 AST 扫描**：`rule/__init__.py:33-244` 的 `extract_module_docstring` 用 `ast` 解析源文件提取 `name`/`doc`/`author`/`tags`/`id` 等元信息（同一逻辑有两套实现：`get_all_rules` 走类继承、`get_all_rules_by_dir` 走 AST 扫描）。规则元信息不是数据，而是源码副产品。

### 2.3 结论：重写的必要性

| 问题         | fanmade 现状     | MVDSL 对策                |
| ---------- | -------------- | ----------------------- |
| 组合爆炸       | O(N²) 手写组合文件   | 管道复合，组合零额外代码（§6）        |
| 规则职责混杂     | 一个类 6 类职责      | 规则只声明语义；求解/渲染/序列化分层（§3） |
| 约束逻辑分散     | 写在每个 Value 对象内 | 六类组合子统一定义，编译器生成约束（§5）   |
| 元信息是源码副产品  | AST 扫描         | 规则注册表 = 数据（§8.3）        |
| 组合优化靠各规则特判 | `combine()` 钩子 | 编译期管道融合 + 后端线性化统一优化     |

### 2.4 值得吸收的工程经验

fanmade 项目在**求解器工程**上积累了实证经验，应吸收其**思路**而非代码：

1. **唯一性验证 = no-good 切割**：解出后追加 `AddBoolOr([变量取反…])` 排除当前解，二次求解；无解则唯一。`impl/summon/solver.py`
2. **增量补偿**：CP-SAT 不支持删约束，用 `model.clone()` + `AddHint`（上轮解作搜索提示）替代真增量
3. **并行假设测试**：`ThreadPoolExecutor` + 每任务独立 `model.clone()` + 独立 solver，实现线程安全
4. **性能配置**：`num_search_workers` 多线程、`linearization_level=2`、`randomize_search` + 固定种子
5. **`Switch` 开关变量体系**：将每条规则/每个位置的条件启用建模为布尔变量，使规则集成为"可组合的假设集合"，支撑 MUS/MCS 提示生成
6. **动态挖洞出题**：每删除一个线索做一次唯一性验证

---

## 3. 架构设计

### 3.1 范式选择：声明式外壳 + 函数式内核

- **谜题描述必须是声明式**：规则本质是"布局满足什么性质"的陈述而非计算过程；谜题需序列化（导入官方关卡库、前端渲染），数据格式天然声明式。
- **规则语义的实现是函数式的**：官方三段式源码已证明规则有代数结构——区域函数 + 约束生成 + 全局谓词，组合规则就是这些函数的复合。
- 纯函数式会丢失序列化与前端渲染能力；纯声明式（有限规则枚举）无法满足可扩展性。**注册表（数据）连接两者**。

### 3.2 四层架构

```
┌─ 声明式外壳（用户所写 · 数据） ─────────────────────────┐
│  L3  谜题描述（Puzzle DSL）                              │
│      board 尺寸/雷数 · rules 列表 · grid token           │
│      sideboards 显式声明 · cell 多角色                   │
│                    ↓                                     │
│  L2  规则代数（组合子库 + 注册表）                       │
│      Region / Weight / Aggregate / Relation / Global     │
│      / Sideboard —— 每条规则 = 组合子的命名实例          │
└──────────────────────────────────────────────────────────┘
                     ↓
┌─ 函数式内核（Python · 代码） ───────────────────────────┐
│  L1  约束编译                                            │
│      管道复合 → 后端无关 IR → 后端适配器                 │
│      适配器：CP-SAT（主）/ Z3（可选）/ csugar（对照）    │
│                    ↓                                     │
│  L0  求解服务                                            │
│      solve · 全解枚举/唯一性验证 · 难度评估 · hint       │
└──────────────────────────────────────────────────────────┘
```

层次职责与依赖方向：**L3 → L2 → L1 → L0 单向依赖**，L1 通过 IR 与后端解耦，换后端不动 L2/L3。

### 3.3 与 fanmade 架构的关键差异

| 维度     | fanmade                                    | MVDSL               |
| ------ | ------------------------------------------ | ------------------- |
| 约束生成位置 | 每个 `AbstractValue` 内写 `create_constraints` | 组合子库统一定义，编译器生成      |
| 规则定义   | Python 类，6 类职责                             | 数据（注册表条目）+ 组合子实例    |
| 组合方式   | 手写组合文件 / `combine()` 特判                    | 管道复合（编译期融合）         |
| 元信息    | AST 扫描源码                                   | 注册表数据（可导出 JSON 给前端） |
| 求解耦合   | 规则直接依赖 `ortools` 与 `Switch`                | 规则层零后端依赖，经 IR 隔离    |

---

## 4. DSL 规范

### 4.1 谜题描述（L3）

规范形式（JSON / YAML）：

```json
{
  "board": { "w": 6, "h": 6, "mines": 10 },
  "rules": ["liar", "encrypted"],
  "grid": [
    [".", "L3", ".", ".", "E2", "."],
    ...
  ],
  "sideboards": [
    { "kind": "permutation", "for": "encrypted", "layout": "shared" },
    { "kind": "error_marks",  "for": "liar" }
  ],
  "cells": {
    "3,4": { "roles": ["mine", "clue"], "clue": { "rule": "V", "value": 3 } }
  }
}
```

设计要点：

- **`rules` 是列表，AND 语义**（与官方 `MetaInfo` 一致），顺序无关
- **`sideboards` 显式声明**——取代官方 `[&&]` + 仲裁属性的隐式推导
- **文本语法糖兼容官方格式**：导入器直接吃 `all_puzzles_dedup.txt` 的行格式（`MetaData` + token 流），编译为上述 JSON

### 4.2 格子模型：多角色

格子不预设"雷 xor 线索"，而是 `roles ⊆ {mine, clue, colored, …}`：

```json
{ "roles": ["mine", "clue"], "clue": { "rule": "V", "value": 3 } }
```

**这是雷线索（未来规则）的免费支持**——只需两点：

1. 约束生成不假设"线索格非雷"：雷格的线索约束照常生成
2. 区域函数显式声明是否含自身（官方 Knight 含自身、Vanilla 不含，这类差异必须成为组合子参数而非隐含约定）

官方已证明该机制可行：mv2 token 以 `F` 开头即"初始可见的雷"且参与面积泛洪计算；mv1 `[$]` 纸笔模式小写字母既计雷又是可见线索。

### 4.3 规则注册表（L2 数据）

每条规则是一个数据条目，而非 Python 类：

```yaml
- id: "1L"
  name: { en: "Liar", zh_CN: "误差" }
  kind: clue                      # clue | global | sideboard
  pipeline:
    region: moore                 # 3x3 九宫
    weight: identity
    aggregate: sum
    relation: { type: offset, deltas: [+1, -1] }
  tags: ["Official", "Clue"]
```

元信息（`name`/`doc`/`author`/`tags`）是**数据**，可直接导出 JSON 供前端使用（对比 fanmade 需 AST 扫描源码）。

---

## 5. 规则代数：六类组合子

线索规则的统一语义是一条管道：

$\text{clue} = \mathrm{Relation}\big(\mathrm{Aggregate}(\mathrm{Weight}(\mathrm{Region}(i,j)))\big)$

| 组合子                | 职责             | 覆盖的规则实例（官方源码为证）                                                            |
| ------------------ | -------------- | -------------------------------------------------------------------------- |
| **Region** 区域      | $(i,j)$ → 格子集合 | 3×3（V）、马步 8 格（K）、半径 2 十字（1X）、上移 3×3（2D）、八向射线（2Q）、沿雷泛洪（2A）、全盘最近雷（2P）、视线（1E） |
| **Weight** 权重      | 每颗雷计入多少        | 恒等（V）、染色 ×2（1M）、染色 − 非染色（1N）                                               |
| **Aggregate** 聚合   | 集合 → 数         | 求和（V）、连续雷组数（1P）、最长连续雷（1W'）、距离积（2P）、面积和（2A）、可见格数（1E）、数墙分段（1W）               |
| **Relation** 关系    | 真实值 ↔ 显示值      | $=$、$\pm 1$（1L/2L）、$\equiv \pmod 3$（2M）、字母置换（2E）                           |
| **Global** 全局谓词    | 整盘布局约束         | 1Q/1C/1T/1O/1D/1S/1B/2H/2S/2G 等，逐条 AND                                     |
| **Sideboard** 副板模式 | 额外未知变量 + 板布局   | 2E 置换矩阵、2L 误差标记、2I 方向掩码、2U 列计数                                             |

**覆盖性论证**：官方 `GetSimpleClueAffectedRegion` 的所有分支可归入 Region；`GetCellConstraint` 的所有 case 可分解为 Weight/Aggregate/Relation 的组合；`BuildMetaConstraints` 的所有分支即 Global；副板相关逻辑即 Sideboard。六类组合子穷尽官方规则语义空间。

---

## 6. 组合规则与可扩展性

### 6.1 问题

官方与 fanmade 都把组合规则当作**新的独立规则**处理：

- 官方：`2L1W`、`2E1M`、`GUESS_LIAR` 等预合成标识，各写专门 case
- fanmade：`rule/Rrule/1L/` 下 21 个手写文件（§2.2）

两者共同后果：**组合数 = 手写组合数**，O(N²) 爆炸。

### 6.2 解法：管道复合

- **线索 × 线索组合 = 管道复合**：编译器逐段合成 IR，不为任何组合写专门代码

  例：`2E&`（Encrypted ∘ Liar）
  ```
  sum(moore(i,j)) → ±1（Liar 误差）→ 置换字母（Encrypted 副板编码）
  ```
- **全局 × 线索组合 = 约束 AND**（本就是列表语义，与官方一致）
- **副板冲突 = 声明式分配**：sideboard 作为显式字段，`[&&]` 分离/共享成为显式参数，不再隐式仲裁

### 6.3 可扩展性验证

| 新机制           | 所需改动                         |
| ------------- | ---------------------------- |
| 雷线索（线索同时是雷）   | **零改动**——cell 多角色模型已支持（§4.2） |
| 新基础规则（如新区域形状） | 新增一个 Region 组合子实例 + 一条注册表条目  |
| 新组合规则         | **零改动**——管道自动复合              |
| 新副板类型         | 新增一个 Sideboard 实例            |
| 3D 规则         | Region/Global 组合子参数化维度       |
| 换求解后端         | 新增 L1 适配器，L2/L3 不动           |

---

## 7. 后端选型

### 7.1 结论：CP-SAT 为主后端

| 维度                       | CP-SAT（OR-Tools）                                            | Z3                 | csugar                       |
| ------------------------ | ----------------------------------------------------------- | ------------------ | ---------------------------- |
| sum-of-bools 线性约束（本项目主体） | **原生最优**：伪布尔/线性传播 + LP 松弛                                   | 需编码到理论层再下译 SAT     | 需 `if` 求和模拟                  |
| 并行                       | **多 worker 默认支持**                                           | 单线程为主              | 无                            |
| 预处理                      | 极强（presolve、对称破除）                                           | 一般                 | 弱                            |
| 批量吞吐（回归/唯一性/难度）          | **明显更快**                                                    | 慢                  | 慢                            |
| 交互式真增量                   | 弱（不能删约束，需 clone + AddHint）                                  | **强**（push/pop）    | 弱                            |
| 表达力                      | 完备：`OnlyEnforceIf`、`AddModuloEquality`、AllDifferent、Circuit | 完备（含非线性/量词，本项目用不上） | **受限**：无 mod/div/pow，乘法仅常数因子 |
| 许可证                      | Apache-2.0                                                  | MIT                | 需查证                          |

**理由**：

1. 本项目约束形态（每格一个布尔 + 大量 $\mathrm{sum}(\text{bools}) = n$ + reify + 少量全局结构）正是 CP-SAT 的原生最优场景
2. csugar 的表达力短板已迫使官方源码手工展开（2M 取模规则写成 `sum==n ∨ sum==n±3` 三析举），而 CP-SAT 有原生 `AddModuloEquality`
3. fanmade 项目实测扛住了动态挖洞出题（每步一次唯一性验证、数万次求解）的负载，是 CP-SAT 够用的实证

### 7.2 后端分层

| 后端         | 角色                       | 状态      |
| ---------- | ------------------------ | ------- |
| **CP-SAT** | 生产主后端                    | v1 实现   |
| **Z3**     | 可选适配器，供高频真增量交互场景         | 阶段四（可选） |
| **csugar** | 对照验证——它是官方游戏真身，是语义保真的金标准 | 阶段四（可选） |

架构上通过 **L1 后端无关 IR** 隔离，三者共用 L2/L3，替换后端不动规则层。

---

## 8. 目录结构与模块划分

### 8.1 目录树

```
D:\dev\mv\MVDSL\
├── PROJECT.md                  # 本文档
├── README.md
├── pyproject.toml              # uv 管理，依赖 ortools
├── mvdsl/                      # 主包（src layout 下为 src/mv_dsl/）
│   ├── ir/                     # L1 约束中间表示（后端无关）
│   │   ├── expr.py             #   Lin / Cmp / And / Or / reify / 表约束 / 取模
│   │   └── eval.py             #   给定赋值检查断言（验证用）
│   ├── backends/               # L1 后端适配器
│   │   ├── cpsat.py            #   主后端（OR-Tools CP-SAT）
│   │   ├── z3.py               #   可选（后续）
│   │   └── csugar.py           #   可选，S 表达式对照（后续）
│   ├── combinators/            # L2 六类组合子：按类别嵌套，抽象基类 + 具体子类（每子类独立文件）
│   │   ├── region/
│   │   │   ├── region.py       #   class Region（抽象基类）
│   │   │   ├── moore.py        #   class RMoore（3x3 九宫，[V]）
│   │   │   ├── knight.py       #   class RKnight（马步 8 格，[K]）
│   │   │   ├── cross.py        #   class RCross（半径 2 十字，[X]）
│   │   │   ├── mini_cross.py   #   class RMiniCross（半径 1 十字，[X']）
│   │   │   └── eyesight.py     #   class REyesight（四方向视线，[E]/[E']）
│   │   ├── weight/
│   │   │   ├── weight.py       #   class Weight（抽象基类）
│   │   │   ├── identity.py     #   class WIdentity（每雷计 1）
│   │   │   ├── dye_double.py   #   class WDyeDouble（染色雷计 2，[M]）
│   │   │   ├── dye_diff.py     #   class WDyeDiff（染色 +1/非染色 -1，[N]）
│   │   │   └── dye_mn.py       #   class WDyeMn（染色 +2/非染色 -1，[M][N]）
│   │   ├── aggregate/
│   │   │   ├── aggregate.py    #   class Aggregate（抽象基类）
│   │   │   ├── sum.py          #   class ASum（求和，[V] 等）
│   │   │   ├── absolute_sum.py #   class AAbsoluteSum（|Σ|，[N]/[NX]/[MN]）
│   │   │   ├── wall_segments.py#   class AWallSegments（数墙段长，[W]）
│   │   │   ├── longest_wall.py #   class ALongestWall（最长段，[W']）
│   │   │   ├── group_count.py  #   class AGroupCount（段数，[P]）
│   │   │   ├── eyesight.py     #   class AEyesight（四向可见格数，[E]）
│   │   │   └── sight_diff.py   #   class ASightDiff（纵横视野差，[E']）
│   │   ├── relation/
│   │   │   ├── relation.py     #   class Relation（抽象基类）
│   │   │   ├── equals.py       #   class RelationEquals（显示 == 真实）
│   │   │   └── offset.py       #   class RelationOffset（显示 == 真实 ± 1，[L]/[LM]）
│   │   ├── constraint/
│   │   │   └── constraint.py  #   class Constraint（抽象基类，全局规则，后续）
│   │   ├── sideboard/
│   │   │   └── sideboard.py    #   class Sideboard（抽象基类，副板，后续）
│   │   └── rule.py             #   class ClueRule：管道 Region∘Weight∘Aggregate∘Relation
│   ├── registry/               # L2 规则注册表（数据）
│   │   ├── rules_mv1.py        #   mv1 规则：id → ClueRule / Constraint 实例
│   │   └── rules_mv2.py        #   mv2 规则（后续）
│   ├── puzzle/                 # L3 谜题描述
│   │   ├── model.py            #   Cell / Clue / Puzzle / Sideboard 模型
│   │   ├── importer_mv1.py     #   mv1 官方格式导入
│   │   └── importer_mv2.py     #   mv2 官方格式导入（含副板）
│   ├── rules/                  # 规则语义（基于组合子管道的薄封装）
│   │   ├── evaluator.py        #   从答案盘计算线索显示值（fill/验证）
│   │   └── compiler.py         #   谜题 → IR 约束
│   ├── solver/                 # L0 求解服务（后续）
│   └── server/                 # 可选：HTTP 适配层（见 §9）
├── tests/
│   ├── test_ir_cpsat.py        # IR / 后端单元测试
│   ├── test_verify_mv1_rules.py# 求值器 vs legacy 基准
│   ├── test_verify_official.py # 官方答案盘是否满足约束
│   ├── test_solve_official.py  # CP-SAT 端到端求解
│   └── test_combinators/       # 组合子单元测试（后续）
└── data/                       # 官方关卡库（不入库，运行时读取）
```

### 8.2 组合子的类体系约定

六类组合子各按**类别嵌套目录**，目录内 `{类别}.py` 为**抽象基类**，
其余文件为**具体子类**（每子类独立文件）。类名前缀约定：

| 类别 | 抽象基类 | 子类前缀 | 示例 |
|---|---|---|---|
| Region | `Region` | `R` | `RMoore` / `RKnight` / `REyesight` |
| Weight | `Weight` | `W` | `WIdentity` / `WDyeDouble` |
| Aggregate | `Aggregate` | `A` | `ASum` / `AWallSegments` / `AEyesight` |
| Relation | `Relation` | `Relation`（全名避免与 R 冲突） | `RelationEquals` / `RelationOffset` |
| Global | `Constraint` | `G` | `GQuad` / `GConnected`（后续） |
| Sideboard | `Sideboard` | `S` | `SPermutation` / `SErrorMarks`（后续） |

一条规则 = 各组合子具体子类的**管道实例**（`rule.py` 的 `ClueRule`）：

$$\\text{clue} = \\mathrm{Relation}(\\mathrm{Aggregate}(\\mathrm{Weight}(\\mathrm{Region}(i,j))))$$

注册表（`registry/`）以**数据**形式登记规则：`id → ClueRule(Region 子类, Weight 子类, Aggregate 子类, Relation 子类)`。
新增规则 = 新增子类（如需）+ 注册表条目；**组合规则零额外代码**（管道天然复合）。
求值器与编译器都只依赖管道的两个方法：`value()`（从答案盘算显示值）与 `encode()`（生成约束），
保证 fill 与约束生成语义一致。

### 8.3 规则注册表示例

```yaml
# registry/rules_14mv1.yaml
- id: "V"
  name: { en: "Vanilla", zh_CN: "标准扫雷" }
  kind: clue
  pipeline: { region: moore, weight: identity, aggregate: sum, relation: eq }
  tags: ["Official", "Clue"]

- id: "1L"
  name: { en: "Liar", zh_CN: "误差" }
  kind: clue
  pipeline:
    region: moore
    weight: identity
    aggregate: sum
    relation: { type: offset, deltas: [1, -1] }
  tags: ["Official", "Clue"]

- id: "1Q"
  name: { en: "Quad", zh_CN: "无方" }
  kind: global
  predicate: quad          # 每个 2x2 至少一雷
  tags: ["Official", "Global"]
```

---

## 9. Server 对接评估（MinesweeperVariants-Vue）

### 9.1 现状

- fanmade 的 server 已拆为**独立 submodule**（`Minesweepervariants-Fanmade/server`），本地未检出，源码不可见
- 前端 `MinesweeperVariants-Vue` 通过 HTTP 调用，**server 地址可配置**，默认 `http://localhost:5050/api/`（`src/composables/useSettings.ts:112`）
- 前端部署在 Cloudflare Pages（`wrangler.jsonc`，静态资源 `./dist`），与 server 分离

### 9.2 API 契约（前端视角）

`MinesweeperVariants-Vue/api.md` 记录的端点：

| 端点          | 方法   | 返回                                                        |
| ----------- | ---- | --------------------------------------------------------- |
| `/reset`    | POST | 无                                                         |
| `/metadata` | GET  | `BoardMetadata`（rules / boards / cells / count / mode）    |
| `/click`    | POST | `ClickResponse`（success / gameover / cells / mines / win） |
| `/new`      | GET  | `NewGameResult`                                           |
| `/hint`     | GET  | `{ hints: Hint[] }`（`condition` / `conclusion`）           |
| `/rules`    | GET  | `RuleData`（规则元信息 + 染色定义）                                  |

前端实际还用到 api.md 未记录的端点（`src/utils/fetchUtils.ts`）：

- `/new_token`（401 后重新取 token，`:94`）
- `/check?taskid=N`（异步任务轮询，`:185`）
- 202 状态码 + `interval`/`progress` 的进度轮询（`:167-175`）
- `taskid` 异步任务模型（`:180`）

### 9.3 对接可行性评估

| 评估项   | 结论                                                                                                                                           |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 技术可行性 | **高**。契约清晰（6 个主端点 + 3 个辅助），前端 server 地址可配置，替换 server 无需改前端                                                                                   |
| 成本    | **中**。需实现 6 个主端点 + token/异步任务机制；难点在 `cells` 的组件化渲染描述（`ComponentConfig` 含 `container`/`text`/`assets`/`template` 四类型），这是 fanmade 渲染体系的核心，耦合较深 |
| 收益    | **中高**。可复用成熟前端（棋盘渲染、交互、设置、主题、规则浏览）                                                                                                           |
| 风险    | `ComponentConfig` 渲染树是 fanmade 特有设计，MVDSL 若要独立表达，需自建等价的渲染描述层                                                                                 |

### 9.4 建议

**分阶段处理，不绑定 v1**：

1. **v1–v4（DSL + 求解器）**：完全不碰 server，专注核心
2. **v5（可选）**：实现 server 适配层，**优先对齐 `/metadata` + `/click` + `/new` + `/rules` 四个核心端点**，先跑通基础对局
3. **v5+（可选）**：补齐 `/hint`（复用 fanmade 的 MUS/MCS 思路，但用我们的 IR 实现）、token、异步任务

**退出条件**：若实现 `/metadata` 的 `ComponentConfig` 渲染树时发现与我们的值模型差异过大（预计在 v5 阶段中期可判定），则放弃对接，改为自建轻量前端或仅提供 JSON API。

---

## 10. 实施路线

| 阶段        | 目标      | 交付物                                                                                         | 完成判据          |
| --------- | ------- | ------------------------------------------------------------------------------------------- | ------------- |
| **一**     | 地基      | L1 IR + CP-SAT 适配器 + L0 solve；L2 的 Region/Weight/Aggregate/Relation 四类组合子；mv1 全部 29 条规则入注册表 | mv1 官方关卡库回归通过 |
| **二**     | 全局与副板   | Global 组合子（mv1 全局规则）+ Sideboard 组合子；L3 谜题模型 + 官方格式导入器                                       | 含副板的关卡可求解     |
| **三**     | 组合与 mv2 | 管道复合编译；mv2 全部线索规则入注册表；`2E&`/`2L&` 等组合专项通过                                                   | 组合规则无需特判即可工作  |
| **四**     | 服务端能力   | 唯一性验证（no-good）、全解枚举、难度评估；可选：Z3 / csugar 对照后端                                                | 唯一性验证与官方结论一致  |
| **五**（可选） | Server  | HTTP 适配层，对齐 4 个核心端点                                                                         | 前端可跑通基础对局     |
| **六**（可选） | 出题器     | 动态挖洞生成唯一解谜题                                                                                 | 能生成可解且唯一的谜题   |

**阶段一至四是 v1 完整范围**，阶段五、六视 §9 评估结果决定。

### 10.1 实施进展（2026-08-28）

| 阶段 | 状态 | 实际交付 |
|---|---|---|
| 一 | **完成** | L1 后端无关 IR（含表约束、取模、reify）+ CP-SAT 适配器（solve / solve_all） |
| 二 | **完成** | 两代官方导入器 + mv1 全部 15 条线索规则约束生成；全局规则未开始 |
| 三 | 进行中 | mv2 规则尚未实现（采样 800 关全部跳过） |
| 四 | 部分 | 唯一性验证 / 全解枚举已可用（no-good 切割）；难度评估按决议后置 |

已验证（详见 README「已验证成果」）：mv1 采样 1500 关全部可编译且答案盘 100% 满足约束；
求值器与 legacy 基准 182 万格 100% 一致；CP-SAT 端到端求解 40/40。

**实施中修正的领域认知**：14mv 是交互式游戏，官方关卡**不保证静态唯一解**
（未揭示格的线索值不在文件中），故正确性判据为「答案盘满足全部约束」，
而非「求解结果 == 答案盘」。唯一解是出题器的要求。

---

## 11. 验证策略

### 11.1 回归测试集

使用官方关卡库 `D:\dev\mv\MineVar2\puzzle\all_puzzles_dedup.txt`（TAB 三字段：标题 / 内容 / 难度串）：

1. 每关断言游戏的**已知解**满足 DSL 编译出的约束（语义正确性）
2. 抽样断言**解唯一**（与官方谜题设计一致）
3. 组合关卡（`[2E][2L]`、`[&&]` 分离副板等）做**专项单元测试**

### 11.2 双后端对照

抽样关卡同时编译到 CP-SAT 与 csugar S 表达式，求解结果须一致。csugar 是官方游戏真身，作为**语义保真金标准**。

### 11.3 组合规则专项

针对 §6 的组合场景编写测试，确保：

- 组合规则的约束 = 各分段约束的复合（而非特判产物）
- 副板冲突在声明式分配下确定性可解

---

## 12. 参考资料

### 12.1 官方游戏反编译源码

| 资料             | 路径                                                                                     | 关键内容                                                                                        |
| -------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 14mv1 主源码      | `D:\dev\mv\MineVar\decompiled\MinesweeperAnalyzer\MinesweeperAnalyzer\`                | `MinesweeperSolver.cs`（1741 行）、`Symbols.cs`（228 行，29 个 `RULE_*`）                            |
| 14mv2 主源码      | `D:\dev\mv\MineVar2\script\`                                                           | `PuzzleGrid.cs:211`（构造 Solver）、`PuzzleDatabase.cs:72-87`（关卡解析）、`PuzzleData.cs:34-87`        |
| **14mv2 规则核心** | `MinesweeperAnalyzer.dll`（未反编译为文件，位于 Godot app_userdata 的 `.mono/assemblies/Release/`） | 用 `DOTNET_ROLL_FORWARD=Major ilspycmd -t MinesweeperAnalyzer.MinesweeperSolver <dll>` 反编译验证 |

**14mv2 规则核心关键符号**（反编译可定位）：

| 符号                                               | 作用                                            | 对应组合子                         |
| ------------------------------------------------ | --------------------------------------------- | ----------------------------- |
| `GetSimpleClueAffectedRegion(rule, i, j)`        | 静态区域（3×3/马步/十字/上移/射线）                         | Region                        |
| `GetClueAffectedRegion(state, i, j)`             | 状态依赖区域（2A 泛洪 / 2P 最近雷 / 2I 副板方向）              | Region（动态）                    |
| `GetCellConstraint(solver, isBomb, i, j, state)` | 逐格约束生成                                        | Weight + Aggregate + Relation |
| `BuildMetaConstraints`                           | 全局规则约束（逐条 AND）                                | Global                        |
| `BuildLiarLinkExpressions`                       | 副板联动（`isBomb[i,j].Then(~isBomb[i,j+offset])`） | Sideboard                     |
| `SeparateStringSuffixNumber`                     | token 解析（规则ID + 数值后缀）                         | L3 导入器                        |
| `CellHasMine`                                    | token 以 `F`/`f` 开头即为雷                         | cell 多角色模型                    |

关键规则实现位置（14mv2 反编译）：

- `[1L]` Liar：`sum == n+1 ∨ sum == n-1`（3517-3537 行）——注意是 **±1 偏差**而非值取反
- `[2M]` Modulo：`sum ≡ n (mod 3)`（3539-3553 行）
- `[2E]` Encrypted：副板置换矩阵，`BuildMetaConstraints` 2126-2150 行生成"每行/每列恰 1 雷"，`BuildConstraints` case 3910-3937 行约束字母格与副板列编码
- `[2A]` Area：从 `(i,j)` 沿已揭示雷 BFS 泛洪（1036-1070 行）
- `[2I]` Incomplete：从副板读取被剔除方向（963-975 行）
- 雷线索：mv2 token 含大写字符则初始可见（5302-5320 行）；`F` = 初始可见的雷

### 12.2 csugar 源码（对照后端参考）

| 资料                  | 路径                                                         | 关键内容                                                                                                                               |
| ------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| csugar（instr3 fork） | `D:\dev\mv\MineVar\third_party\csugar_forks\instr3_csugar` | C++ Sugar 重实现 + MiniSat                                                                                                            |
| 表达式类型枚举             | `include\csp\expr.h:13-45`                                 | 全部算子定义                                                                                                                             |
| 转换器（表达力边界）          | `src\conv\converter.cpp`                                   | `div/mod/pow/min/max` 未实现（:300 TODO）；`mul` 仅常数因子（:269-288）；`alldifferent` 展开为两两 ≠（:137-146）；reify 靠 `if`（:289-299）+ 析取重写（:120-131） |
| **文本 DSL token 表**  | `src\csp\parser.cpp:14-45`                                 | 对照适配器需输出此格式                                                                                                                        |
| 调用流程                | `src\integrated\integrated.cpp:96-146`                     | CSP → Converter → ICSP（域传播）→ Simplifier → Encoder（order encoding）→ SAT → MiniSat                                                   |
| C# 封装（游戏侧）          | `D:\dev\mv\MineVar\decompiled\CSPCore\CSPCore\`            | `Solver.cs`、`BoolExpr.cs`、`IntExpr.cs`（`CountTrue` = `sum(b.Cond(1,0))`，:78-95）、`Graph.cs`                                         |

**14mv2 的 csugar 新增**：`graph-area`（`ActiveVerticesConnectedArea`）、`SolveAll`、`SolveSingleBlocked`——**仅从 DLL 元数据提取，本地无源码**。

### 12.3 规则描述文档

| 资料          | 路径                                                                  |
| ----------- | ------------------------------------------------------------------- |
| 14 种变体规则描述  | `D:\dev\mv\MineVar2\14种扫雷变体规则.docx`                                 |
| **已提取的文本版** | `D:\dev\mv\MVDSL\.workbuddy\rules_docx_extract.txt`（64 段 / 2387 字符） |

> 注：该文件经 editor_sdk 打开失败（"document is not open"），改用 Python 解包 docx 提取，内容完整。

### 12.4 fanmade 项目（本地拷贝 `D:\dev\mv\Minesweepervariants-Fanmade`）

| 用途              | 路径                                                                      | 关键字                                                                                                                    |
| --------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **规则接口契约**      | `MinesweeperVariants/minesweepervariants/abs/rule.py`                   | `AbstractRule.create_constraints`（:330）、`combine`（:370）、`AbstractValue.create_constraints`（:517）、`suggest_total`（:341） |
| 线索规则基类          | `MinesweeperVariants/minesweepervariants/abs/Rrule.py`                  | `AbstractClueRule.fill`（:34）、`AbstractClueValue`（:64）                                                                  |
| 布局规则基类          | `MinesweeperVariants/minesweepervariants/abs/Lrule.py`                  | `AbstractMinesRule`                                                                                                    |
| 交互规则基类          | `MinesweeperVariants/minesweepervariants/abs/Mrule.py`                  | `AbstractMinesClueRule`                                                                                                |
| **CP-SAT 求解核心** | `MinesweeperVariants/minesweepervariants/impl/summon/solver.py`（733 行）  | `Switch`、`solver_by_csp`、`deduced_by_csp`、`hint_by_csp`、`_hint_by_csp`（MUS/MCS）、`add_board_solution_hints`             |
| 出题器             | `MinesweeperVariants/minesweepervariants/impl/summon/summon.py`（1152 行） | `create_puzzle`（:394）、`dynamic_dig_unique`（:552）、`dig_unique`                                                          |
| 游戏状态机           | `MinesweeperVariants/minesweepervariants/impl/summon/game.py`（1171 行）   | `GameSession`（:196）、`click`/`mark`/`step`/`deduced`/`hint`                                                             |
| 题板容器            | `MinesweeperVariants/minesweepervariants/board.py`（1058 行）              | `get_variable`（:649）、`get_model`（:328）、`clone`（:140）、`clear_variable`（:669）、`batch`（:839）                              |
| 规则扫描（元信息）       | `rule/__init__.py`                                                      | `extract_module_docstring`（:33）、`scan_module_docstrings`（:247）、`get_all_rules`（:360）、`get_all_rules_by_dir`（:416）      |
| 规则实现样例（最简）      | `rule/Rrule/V.py`（119 行）                                                | `RuleV.fill`（:38）、`ValueV.create_constraints`（:102）                                                                    |
| **组合爆炸证据**      | `rule/Rrule/1L/`（21 文件 / 2647 行）                                        | `1L.py:29` `Rule1L`；`1L1W.py:152` `Rule1L1W(AbstractClueRule)` 无复用                                                     |
| 依赖声明            | `MinesweeperVariants/pyproject.toml`                                    | `ortools>=9.13.4784`；server 组含 flask / waitress / orjson                                                               |
| 前端 API 契约       | `MinesweeperVariants-Vue/api.md`                                        | 6 个端点 + 类型定义                                                                                                           |
| 前端请求封装          | `MinesweeperVariants-Vue/src/utils/fetchUtils.ts`                       | `getApiEndpoint`（:230）、`/new_token`（:94）、`/check`（:185）、202 进度（:167）                                                   |
| 前端 server 配置    | `MinesweeperVariants-Vue/src/composables/useSettings.ts:112`            | 默认 `http://localhost:5050/api/`                                                                                        |
| 前端部署            | `MinesweeperVariants-Vue/wrangler.jsonc`                                | Cloudflare Pages，静态 `./dist`                                                                                           |

### 12.5 其他

| 资料         | 路径                                                       |
| ---------- | -------------------------------------------------------- |
| 官方关卡库（回归集） | `D:\dev\mv\MineVar2\puzzle\all_puzzles_dedup.txt`        |
| 教程关卡       | `D:\dev\mv\MineVar2\puzzle\tutorial\tutorial_[1B]_0.txt` |
| mv1 关卡回放   | `D:\dev\mv\MineVar2\puzzle\prequel_puzzles.txt`          |

---

## 13. 风险与待定事项

### 13.1 风险

| 风险                          | 影响                    | 缓解                                                |
| --------------------------- | --------------------- | ------------------------------------------------- |
| **许可证**：fanmade 项目为 GPL-3.0 | 若复用其代码，MVDSL 会被传染     | **只借鉴算法思路，不搬代码**；MVDSL 独立实现，建议采用 Apache-2.0 / MIT |
| 14mv2 规则核心无源码               | 规则语义需从 DLL 反编译推断，可能失真 | 每实现一条规则用官方关卡库回归验证；csugar/Z3 双后端交叉验证               |
| 组合规则语义可能与官方不完全一致            | 组合关卡验证失败              | 以官方关卡库的组合关卡为准（§11.3）                              |
| `graph-area` 无本地源码          | 2A 类面积约束实现依赖推断        | 用 Z3/CP-SAT 自实现（表达力足够），不必复刻 csugar 实现             |
| Server 对接成本超预期              | 阶段五延期                 | §9.4 已设退出条件，可降级为纯 JSON API                        |

### 13.2 待定事项（需确认）

1. **谜题输入格式**：是否直接兼容 `all_puzzles_dedup.txt`（建议：导入器 + 原生 JSON 两者都做）？
2. **难度评估**（对齐官方 `SolutionSummary` 直方图）是否进 v1 范围？
3. **是否需要前端直接求解**（CP-SAT 无成熟 wasm；Z3 有）？若需要，可能需保留 Z3 适配器。
4. **许可证选择**：建议 Apache-2.0（与 OR-Tools 一致），需确认。
5. **项目命名与包名**：暂定 `MVDSL` / `mvdsl`，需确认。
6. **是否覆盖 fanmade 社区的 369 个扩展规则**？建议 v1 只覆盖官方 14mv1/2，社区规则作为后续迁移评估项。
