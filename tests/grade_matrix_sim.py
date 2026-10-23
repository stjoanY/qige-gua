# -*- coding: utf-8 -*-
"""
判级矩阵仿真调参（开发期工具，不进交付物）
================================================
目的：验证「体用生克 × 体卦旺衰 → 七档签级 + 变卦修正」矩阵
     能否逼近玩法总监拍板的分布目标：
     上上 8% / 上 15% / 中上 20% / 中 15% / 中下 15% / 下 12% / 下下 8%
方法：以 meihua.py 为计算基准，蒙特卡洛仿真问事签的卦分布
     （哈希分化后问事签在 64 卦 × 6 动爻上近似均匀），随机月支。
输出：各矩阵参数下的实际分布 vs 目标分布。
"""
import importlib.util
import random
import sys
from collections import Counter

spec = importlib.util.spec_from_file_location(
    "meihua", r"C:\Users\stjoa\.workbuddy\skills\meihua-yishu\scripts\meihua.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

LEVELS = ["上上", "上", "中上", "中", "中下", "下", "下下"]
TARGET = [0.08, 0.15, 0.20, 0.15, 0.15, 0.12, 0.08]
MONTHS = list("寅卯辰巳午未申酉戌亥子丑")

# 关系与旺衰的分数口径（与参考引擎 wuxing_relation / WANGSHUAI 表一致）
REL_SCORE = {"用生体": 2, "比和": 1, "体克用": 0, "体生用": -1, "用克体": -2}


def raw_score(upper, lower, moving, month_branch):
    """复刻 meihua.paipan 的体用/生克/旺衰口径，返回 (主卦分, 变卦关系名)。"""
    lines = m.gua_lines(upper, lower)
    if moving <= 3:
        ti, yong = upper, lower
    else:
        ti, yong = lower, upper
    ti_wx = m.GUA_WUXING[ti]
    yong_wx = m.GUA_WUXING[yong]
    rel_main = m.wuxing_relation(ti_wx, yong_wx)[0]
    bi_u, bi_l = m.bian_gua(lines, moving)
    yong_bian = bi_l if moving <= 3 else bi_u
    rel_bian = m.wuxing_relation(ti_wx, m.GUA_WUXING[yong_bian])[0]

    # 用卦旺衰按经典梅花「用卦为主、体卦参看」加权，这里实现为体:用=2:1
    ws_ti = m.wangshuai_of(ti_wx, month_branch)
    ws_yong = m.wangshuai_of(yong_wx, month_branch)
    return rel_main, rel_bian, ws_ti, ws_yong


def evaluate(upper, lower, moving, month_branch, ws_weight, bin_edges, bian_shift):
    rel_main, rel_bian, ws_ti, ws_yong = raw_score(upper, lower, moving, month_branch)

    def ws_val(s):
        return {"旺": 1.0, "相": 0.5, "休": 0.0, "囚": -0.5, "死": -1.0}[s]

    s = REL_SCORE[rel_main] + ws_weight * ws_val(ws_ti) + (1 - ws_weight) * ws_val(ws_yong)
    # 分数映射七档：bin_edges 为 7 档的分界（6 个阈值，降序判定）
    lv = 7
    for i, edge in enumerate(bin_edges):   # edge 依次为 s>=e1→上上 ...
        if s >= edge:
            lv = i + 1
            break
    # 变卦修正：变卦关系优于主卦 → 升一档(变好)，劣 → 降一档(变差)
    if bian_shift:
        if REL_SCORE[rel_bian] > REL_SCORE[rel_main]:
            lv = max(1, lv - 1)
        elif REL_SCORE[rel_bian] < REL_SCORE[rel_main]:
            lv = min(7, lv + 1)
    return lv


def simulate(ws_weight, bin_edges, bian_shift, n=300000, seed=42):
    rnd = random.Random(seed)
    cnt = Counter()
    for _ in range(n):
        u = rnd.randint(1, 8)
        l = rnd.randint(1, 8)
        mv = rnd.randint(1, 6)
        mb = rnd.choice(MONTHS)
        cnt[evaluate(u, l, mv, mb, ws_weight, bin_edges, bian_shift)] += 1
    return [cnt[i] / n for i in range(1, 8)]


def report(name, dist):
    err = sum(abs(a - b) for a, b in zip(dist, TARGET))
    print(f"--- {name}  总偏差={err*100:.1f}个百分点 ---")
    print(f"{'档':<4}{'目标':>6}{'实际':>8}")
    for lv, t, d in zip(LEVELS, TARGET, dist):
        print(f"{lv:<4}{t*100:>5.0f}%{d*100:>7.1f}%")


if __name__ == "__main__":
    # 候选参数组：旺衰权重 / 七档分界 / 变卦修正开关
    CANDIDATES = [
        # (名称, 体用旺衰权重, 分界, 变卦修正)
        ("A 体卦全权重+修正", 1.0, [2.5, 2.0, 1.0, 0.0, -1.0, -2.0], True),
        ("B 体卦全权重无修正", 1.0, [2.5, 2.0, 1.0, 0.0, -1.0, -2.0], False),
        ("C 体2用1+修正", 2/3, [2.5, 1.8, 1.0, -0.2, -1.0, -1.8], True),
        ("D 体2用1+修正(宽界)", 2/3, [2.2, 1.6, 0.9, -0.3, -1.1, -1.7], True),
    ]
    for name, w, edges, shift in CANDIDATES:
        report(name, simulate(w, edges, shift))
        print()
