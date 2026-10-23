# -*- coding: utf-8 -*-
"""ti+off（体卦旺衰、无变卦修正）的阈值变体手测 + 真实起卦分布验证。
矩阵口径：s = 主卦关系分 + 体卦旺衰值；档 = f(s)，对称分箱候选。"""

import importlib.util
from collections import Counter

spec = importlib.util.spec_from_file_location(
    "meihua", r"C:\Users\stjoa\.workbuddy\skills\meihua-yishu\scripts\meihua.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

LEVELS = ["上上", "上", "中上", "中", "中下", "下", "下下"]
TARGET = [0.08, 0.15, 0.20, 0.15, 0.15, 0.12, 0.08]
MONTHS = list("寅卯辰巳午未申酉戌亥子丑")
REL_SCORE = {"用生体": 2, "比和": 1, "体克用": 0, "体生用": -1, "用克体": -2}
WS_VAL = {"旺": 1.0, "相": 0.5, "休": 0.0, "囚": -0.5, "死": -1.0}


def s_of(u, l, mv, mb):
    lines = m.gua_lines(u, l)
    ti, yong = (u, l) if mv <= 3 else (l, u)
    ti_wx, yong_wx = m.GUA_WUXING[ti], m.GUA_WUXING[yong]
    rel_main = m.wuxing_relation(ti_wx, yong_wx)[0]
    ws = WS_VAL[m.wangshuai_of(ti_wx, mb)]
    return REL_SCORE[rel_main] + ws


UNIFORM = [(s_of(u, l, mv, mb), 1)
           for u in range(1, 9) for l in range(1, 9)
           for mv in range(1, 7) for mb in MONTHS]


def dist(events):
    c = Counter()
    for s, w in events:
        c[GRADE(s)] += w
    t = sum(c.values())
    return [c[i] / t for i in range(1, 8)]


def show(name, events):
    d = dist(events)
    dev = sum(abs(a - b) for a, b in zip(d, TARGET))
    hua = sum(d[4:])
    print(f"--- {name}  L1={dev*100:.1f}pct  化解率={hua*100:.1f}% ---")
    print("  " + " / ".join(f"{lv}{p*100:.1f}%" for lv, p in zip(LEVELS, d)))


# 候选分箱（grade(s) 返回 1-7）：全部无变卦修正、体卦旺衰
def make_grade(edges):
    """edges: 6 个降序阈值 [上上下界, 上, 中上, 中, 中下, 下]"""
    def g(s):
        for i, e in enumerate(edges):
            if s >= e:
                return i + 1
        return 7
    return g


CANDIDATES = [
    ("M1 完美对称(2.5/1.5/0.5/0/-1.0/-2.0)",
     [2.5, 1.5, 0.5, 0.0, -1.0, -2.0]),
    ("M5 贴化解率(-0.5归中,2.5/1.5/0.5/-0.5/-1.0/-2.0)",
     [2.5, 1.5, 0.5, -0.5, -1.0, -2.0]),
    ("M2 对称+中下窄",
     [2.5, 1.5, 0.5, -0.5, -1.5, -2.5]),
    ("M3 对称+下下收窄",
     [2.5, 1.5, 0.5, 0.0, -1.0, -1.5]),
    ("M4 中带加宽(±0.5归中)",
     [2.5, 1.5, 1.0, -1.0, -1.5, -2.5]),
]

# 各分值质量（均匀事件空间）
MASS = Counter()
for s, w in UNIFORM:
    MASS[s] += w
TOT = sum(MASS.values())
print("各 s 分值占比：", "  ".join(f"{s:+.1f}:{MASS[s]/TOT*100:.1f}%" for s in sorted(MASS, reverse=True)))
print()

for name, edges in CANDIDATES:
    GRADE = make_grade(edges)
    show(name, UNIFORM)
    print()

# ============ 真实起卦分布验证（对最终候选再跑） ============
def events_daily():
    """每日一签：2025-01-01..2026-12-31 全枚举，固定午时(时支数7)"""
    out = []
    for y in (2025, 2026):
        jdn0 = m.jdn_from_gregorian(y, 1, 1)
        jdn1 = m.jdn_from_gregorian(y, 12, 31)
        for jdn in range(jdn0, jdn1 + 1):
            gy, gm, gd = m.gregorian_from_jdn(jdn)
            ly, lm, ld, _ = m.solar_to_lunar(gy, gm, gd)
            _, yz = m.year_ganzhi(gy, gm, gd)
            yb = m.DIZHI.index(yz) + 1
            u, l, mv, _ = m.qigua_by_time(yb, lm, ld, 7)
            mb = m.solar_month_branch(gm, gd)
            out.append((s_of(u, l, mv, mb), 1))
    return out


def events_ask():
    """问事签（物数占变体）：字数2-30按现实先验 + 白天时支 + 月支均匀，粗估"""
    import math
    out = []
    hours = [5, 6, 7, 8, 9, 10, 11, 12, 1]  # 辰..亥+子（7:00-23:59）
    for n in range(2, 31):
        w_n = math.exp(-((n - 10) / 5.0) ** 2)  # 字数先验峰≈10字
        a = (n + 1) // 2
        b = n // 2
        for hb in hours:
            for mb in MONTHS:
                u = a % 8 or 8
                l = (b + hb) % 8 or 8
                mv = (n + hb) % 6 or 6
                out.append((s_of(u, l, mv, mb), w_n))
    return out


print("====== 真实起卦分布验证 ======")
for name, edges in CANDIDATES[:2]:
    GRADE = make_grade(edges)
    show(f"{name} · 每日一签(730天全枚举)", events_daily())
    show(f"{name} · 问事签(字数先验粗估)", events_ask())
    print()
