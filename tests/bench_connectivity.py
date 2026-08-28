"""csugar（官方 graph 约束）vs CP-SAT（我们的层编码）连通性性能对比。

对同一批 [C][T] 官方关卡：
- csugar 方案：`graph-active-vertices-connected`（Tarjan 传播器，官方 1C 实现）
- CP-SAT 方案：我们的 BFS 层编码（fanmade 思路）

注意公平性：csugar 单线程 SAT；CP-SAT 默认 8 worker。
"""

from __future__ import annotations

import ctypes
import sys
import time

sys.path.insert(0, "src")

from mv_dsl.backends.cpsat import solve, SolverConfig
from mv_dsl.puzzle.importer_mv1 import import_puzzle, parse_level_id
import sys as _s; _s.path.insert(0, "tests")
from test_solve_official import fill_mv1_clues

CSUGAR_DLL = r"D:/dev/mv/MineVar/build/csugar-windows-x64/csugar.dll"
PATH_MV1 = r"D:/dev/mv/MineVar/puzzle/all_puzzles_dedup.txt"


def build_csugar_query(p) -> str:
    """从 [C][T] 关卡生成 csugar S 表达式（雷数 + V 线索 + 无三连 + 八连通）。"""
    w, h = p.width, p.height
    n = w * h
    lines = [f"(bool b{i})" for i in range(n)]
    vid = {(r, c): r * w + c for r in range(h) for c in range(w)}

    def bools(pts):
        return " ".join(f"(if b{vid[p]} 1 0)" for p in pts)

    # 雷总数
    lines.append(f"(= (+ {bools([(r,c) for r in range(h) for c in range(w)])}) {p.mine_count})")
    # V 线索
    for r, c, cell in p.iter_cells():
        if cell.clue is not None and cell.clue.rule == "V" and cell.clue.value is not None:
            neigh = [
                (r + dr, c + dc)
                for dr, dc in ((0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1))
                if 0 <= r+dr < h and 0 <= c+dc < w
            ]
            lines.append(f"(= (+ {bools(neigh)}) {cell.clue.value})")
    # 无三连 [T]：每 3 连窗口 ≤ 2
    for r in range(h):
        for c in range(w):
            for deltas in (((-1,-1),(0,0),(1,1)), ((-1,1),(0,0),(1,-1)), ((-1,0),(0,0),(1,0)), ((0,-1),(0,0),(0,1))):
                pts = [(r+dr, c+dc) for dr, dc in deltas]
                if all(0 <= x < h and 0 <= y < w for x, y in pts):
                    lines.append(f"(<= (+ {bools(pts)}) 2)")
    # 八连通 [C]：graph-active-vertices-connected
    edges = set()
    for r in range(h):
        for c in range(w):
            for dr, dc in ((0,1),(1,0),(1,1),(1,-1)):
                nr, nc = r+dr, c+dc
                if 0 <= nr < h and 0 <= nc < w:
                    edges.add((r*w+c, nr*w+nc))
    edge_str = " ".join(f"{a} {b}" for a, b in sorted(edges))
    lines.append(f"(graph-active-vertices-connected {n} {len(edges)} {' '.join(f'b{i}' for i in range(n))} {edge_str})")
    lines.append("?")
    return "\n".join(lines) + "\n"


def main(limit: int = 5) -> None:
    dll = ctypes.CDLL(CSUGAR_DLL)
    call = dll.Call
    call.restype = ctypes.c_char_p
    call.argtypes = [ctypes.c_char_p]

    picked = []
    with open(PATH_MV1, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0 or not line.strip():
                continue
            rules = parse_level_id(line.split("\t")[0])[0]
            if set(rules) == {"C", "T"}:
                picked.append(fill_mv1_clues(import_puzzle(line)))
                if len(picked) >= limit:
                    break

    t_cs = t_cp = 0.0
    for p in picked:
        q = build_csugar_query(p)
        t0 = time.time()
        res = call(q.encode())
        dt_cs = time.time() - t0
        cs_ok = res is not None and res.decode().startswith("s SAT")
        t_cs += dt_cs

        from mv_dsl.rules.compiler import compile_puzzle

        cp_model = compile_puzzle(p).model
        t0 = time.time()
        r = solve(cp_model, SolverConfig(num_workers=8))
        dt_cp = time.time() - t0
        t_cp += dt_cp
        print(f"{p.level_id[:40]}  csugar {dt_cs*1000:6.0f}ms ({'SAT' if cs_ok else '??'})   "
              f"CP-SAT {dt_cp*1000:6.0f}ms ({r.status})")

    print(f"\n合计 {limit} 关: csugar {t_cs*1000:.0f}ms (单线程) vs CP-SAT {t_cp*1000:.0f}ms (8 workers)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
