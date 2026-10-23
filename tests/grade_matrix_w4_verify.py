# -*- coding: utf-8 -*-
"""W4 判级口径的阈值区间复验：确认固化后的阈值表 reproduce DP 最优分布。
W4 口径：
  s = 主卦关系分 + (2×体卦旺衰值 + 1×用卦旺衰值)/3
  基准档（阈值含下界）：
    s ≥ 2.50 → 上上 | ≥1.40 → 上 | ≥1.17 → 中上 | ≥-0.50 → 中 | ≥-1.42 → 下 | 其余 → 下下
  变卦修正：变卦关系优于主卦 → 升一档（恒生效）；
            劣于主卦 → 降一档（仅当主卦关系分 ≤ 0，"吉不轻破"）；clamp [上上,下下]
"""
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


def base_level(s):
    if s >= 2.50:
        return 1
    if s >= 1.40:
        return 2
    if s >= 1.17:
        return 3
    if s >= -0.50:
        return 4
    if s >= -1.42:
        return 6
    return 7


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
                s = REL_SCORE[rel_main] + (2 * WS_VAL[m.wangshuai_of(ti_wx, mb)]
                                           + WS_VAL[m.wangshuai_of(yong_wx, mb)]) / 3
                lv = base_level(s)
                if REL_SCORE[rel_bian] > REL_SCORE[rel_main]:
                    lv = max(1, lv - 1)
                elif REL_SCORE[rel_bian] < REL_SCORE[rel_main] and REL_SCORE[rel_main] <= 0:
                    lv = min(7, lv + 1)
                cnt[lv] += 1

total = sum(cnt.values())
print(f"{'档':<4}{'目标':>6}{'复验':>8}")
dev = 0
for i in range(7):
    p = cnt[i + 1] / total
    dev += abs(p - TARGET[i])
    print(f"{LEVELS[i]:<4}{TARGET[i]*100:>5.0f}%{p*100:>7.1f}%")
print(f"L1总偏差={dev*100:.1f}个百分点  化解触发率={sum(cnt[i] for i in (5,6,7))/total*100:.1f}%")
print("（对照 DP 最优：8.0 个百分点 / 33.2%）")
