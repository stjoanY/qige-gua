# -*- coding: utf-8 -*-
"""
判级矩阵选型 v3（约束版：七档均有固有分箱区间，语义可解释）
============================================================
在 v2（全覆盖爬山）基础上加约束：基准档七档每档至少含 1 个 s 分值
（即 bounds 严格递增、第7档非空）。ti 模式 s 仅 13 个离散值 → 穷举全部
C(12,6)=924 种分箱；t2y1 模式 s 有 ~37 值 → 带约束爬山。
目的：让每档都有"天然归属"，中上/中下不至完全依赖变卦修正。
"""
import importlib.util
import random
from collections import Counter
from itertools import combinations

spec = importlib.util.spec_from_file_location(
    "meihua", r"C:\Users\stjoa\.workbuddy\skills\meihua-yishu\scripts\meihua.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

LEVELS = ["上上", "上", "中上", "中", "中下", "下", "下下"]
TARGET = [0.08, 0.15, 0.20, 0.15, 0.15, 0.12, 0.08]
MONTHS = list("寅卯辰巳午未申酉戌亥子丑")
REL_SCORE = {"用生体": 2, "比和": 1, "体克用": 0, "体生用": -1, "用克体": -2}
WS_VAL = {"旺": 1.0, "相": 0.5, "休": 0.0, "囚": -0.5, "死": -1.0}


def enum_events(ws_mode, corr_mode):
    scale = 2 if ws_mode == "ti" else 6
    cnt = Counter()
    for u in range(1, 9):
        for l in range(1, 9):
            for mv in range(1, 7):
                lines = m.gua_lines(u, l)
                ti, yong = (u, l) if mv <= 3 else (l, u)
                ti_wx, yong_wx = m.GUA_WUXING[ti], m.GUA_WUXING[yong]
                rel_main = m.wuxing_relation(ti_wx, yong_wx)[0]
                bi_u, bi_l = m.bian_gua(lines, mv)
                yong_bian = bi_l if mv <= 3 else bi_u
                rel_bian = m.wuxing_relation(ti_wx, m.GUA_WUXING[yong_bian])[0]
                for mb in MONTHS:
                    ws = WS_VAL[m.wangshuai_of(ti_wx, mb)] if ws_mode == "ti" else \
                        (2 * WS_VAL[m.wangshuai_of(ti_wx, mb)] + WS_VAL[m.wangshuai_of(yong_wx, mb)]) / 3
                    delta = 0
                    if corr_mode != "off":
                        if REL_SCORE[rel_bian] > REL_SCORE[rel_main]:
                            delta = -1
                        elif REL_SCORE[rel_bian] < REL_SCORE[rel_main]:
                            if corr_mode == "full" or (corr_mode == "asym" and REL_SCORE[rel_main] <= 0):
                                delta = +1
                    cnt[(int(round(scale * (REL_SCORE[rel_main] + ws))), delta)] += 1
    return cnt, scale


def prep(cnt):
    s_vals = sorted(set(k for k, _ in cnt), reverse=True)
    dh = {k: Counter() for k in s_vals}
    for (k, d), c in cnt.items():
        dh[k][d] += c
    total = sum(cnt.values())
    return s_vals, dh, total


def dev_of(bounds, s_vals, dh, total):
    """bounds: 6 个严格递增索引（各档末索引），第7档延伸到末尾 → 七档全非空"""
    hist = [0] * 7
    idx = 0
    for j, b in enumerate(bounds):
        for i in range(idx, b + 1):
            for d, c in dh[s_vals[i]].items():
                hist[max(0, min(6, j + d))] += c
        idx = b + 1
    for i in range(idx, len(s_vals)):
        for d, c in dh[s_vals[i]].items():
            hist[max(0, min(6, 6 + d))] += c
    return sum(abs(hist[i] / total - TARGET[i]) for i in range(7)), hist


def search(ws_mode, corr_mode):
    cnt, scale = enum_events(ws_mode, corr_mode)
    s_vals, dh, total = prep(cnt)
    n = len(s_vals)
    if n <= 15:
        best = (float("inf"), None, None)
        for combo in combinations(range(1, n), 6):
            bounds = list(combo[0:1]) + []  # placeholder
        # 内部边界：0 < b1 < ... < b6 < n-1，共 6 个内部点
        for combo in combinations(range(1, n - 1), 6):
            bounds = [-1] + list(combo)  # b0=combo[0]-1 使第1档非空
            bounds = list(combo)
            d, h = dev_of(bounds, s_vals, dh, total)
            if d < best[0]:
                best = (d, bounds, h)
    else:
        rnd = random.Random(11)
        best = (float("inf"), None, None)
        for r in range(60):
            if r == 0:
                bounds = [round(n * (j + 1) / 7) - 1 for j in range(6)]
                bounds = sorted(set(bounds))
                while len(bounds) < 6:
                    bounds.append(min(n - 2, bounds[-1] + 1))
            else:
                bounds = sorted(rnd.sample(range(1, n - 1), 6))
            if len(set(bounds)) < 6:
                continue
            cur, _ = dev_of(bounds, s_vals, dh, total)
            improved = True
            while improved:
                improved = False
                for j in range(6):
                    for cand in (bounds[j] - 2, bounds[j] - 1, bounds[j] + 1, bounds[j] + 2):
                        if cand < 1 or cand > n - 2:
                            continue
                        if j > 0 and cand <= bounds[j - 1]:
                            continue
                        if j < 5 and cand >= bounds[j + 1]:
                            continue
                        if cand in bounds:
                            continue
                        old = bounds[j]
                        bounds[j] = cand
                        d2, _ = dev_of(bounds, s_vals, dh, total)
                        if d2 < cur:
                            cur = d2
                            improved = True
                        else:
                            bounds[j] = old
            if cur < best[0]:
                best = (cur, list(bounds), dev_of(bounds, s_vals, dh, total)[1])
    return best, s_vals, total, scale


if __name__ == "__main__":
    for ws_mode in ("ti", "t2y1"):
        for corr in ("full", "asym", "up", "off"):
            (dev, bounds, hist), s_vals, total, scale = search(ws_mode, corr)
            name = f"{ws_mode}+{corr}"
            print(f"=== {name}  L1={dev*100:.1f}pct  化解率={sum(hist[4:])/total*100:.1f}% ===")
            print(f"{'档':<4}{'目标':>6}{'实际':>8}")
            for i in range(7):
                print(f"{LEVELS[i]:<4}{TARGET[i]*100:>5.0f}%{hist[i]/total*100:>7.1f}%")
            segs = []
            idx = 0
            for j, b in enumerate(bounds):
                segs.append(f"{LEVELS[j]}:{s_vals[idx]/scale:+.2f}~{s_vals[b]/scale:+.2f}")
                idx = b + 1
            if idx < len(s_vals):
                segs.append(f"{LEVELS[6]}:{s_vals[idx]/scale:+.2f}~{s_vals[-1]/scale:+.2f}")
            print("分箱:", "; ".join(segs))
            print()
