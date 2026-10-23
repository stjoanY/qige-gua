# -*- coding: utf-8 -*-
"""
判级矩阵最优分箱（精确枚举 + DP，替代盲试参数）
==================================================
【已废弃 · 2026-10 架构组复核结论】本脚本的切分枚举允许 cuts[6] < n-1，
导致尾部 s 值未分配（最优解最多丢弃约 12% 事件，各档求和仅 88%，
分布按 total 归一后系统性失真），W1-W5 结果均不可信。
已由 grade_matrix_hillclimb.py（v2 无约束全覆盖）与
grade_matrix_hillclimb2.py（v3 七档非空约束）+ grade_matrix_final.py（定稿验证）
取代。正式口径见 docs/口径定稿-起卦与判级-v1.md。
--------------------------------------------------------------
事实：问事签经哈希分化后在 64卦×6动爻 上近似均匀 → 8×8×6=384 种
     卦型等概率，叠加 12 月支等概率 → 4608 个等概率基本事件，可精确枚举。
方法：对每个事件算 (主卦分s, 变卦修正delta) 的联合分布，
     再用 DP 求最优的「s→基准档」单调映射，使七档分布逼近目标。
变卦修正语义（经典口径，保持不变）：
     变卦关系优于主卦→升一档；劣于主卦→降一档； clamp 到 [1,7]。
     注：该语义天然压缩两端（最优关系无法再优、最劣无法再劣），属口径固有性质。
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


def events(ws_weight, use_yong_ws, mode):
    """枚举全部 4608 个等概率事件 → Counter{(s 分值四舍五入到1/6, delta)}
    mode: full=变卦修正全开 | asym=吉不轻破(升级恒生效,降级仅主卦分<=0时生效) | off=无修正"""
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
                    ws = WS_VAL[m.wangshuai_of(ti_wx, mb)]
                    if use_yong_ws:
                        ws = ws_weight * ws + (1 - ws_weight) * WS_VAL[m.wangshuai_of(yong_wx, mb)]
                    delta = 0
                    if mode != "off":
                        if REL_SCORE[rel_bian] > REL_SCORE[rel_main]:
                            delta = -1
                        elif REL_SCORE[rel_bian] < REL_SCORE[rel_main]:
                            if mode == "full" or REL_SCORE[rel_main] <= 0:
                                delta = +1
                    # 以 1/12 为刻度离散化，规避浮点
                    key = (int(round(12 * (REL_SCORE[rel_main] + ws))), delta)
                    cnt[key] += 1
    return cnt


def dp_optimal(cnt, total, bian_on):
    """s 降序（高分=吉在前）→ 基准档非降（第1组=上上）。DP 求 L1 偏差最小的映射。
    返回 (最优偏差, cuts, hist)"""
    s_vals = sorted(set(k[0] for k in cnt), reverse=True)  # 高分(吉)在前 → 上上
    # 每个基本事件的最终档 = clamp(基准档 + delta)
    # delta 分布随 (s, 事件) 而定，须按事件聚合：把每个 (s, delta) 的计数
    # 转成「基准档=b 时落入各最终档的数量」
    INF = float("inf")
    # dp[i][b] = 处理完前 i 个 s 值、最后一个基准档为 b 的最小累计绝对偏差
    # 逐层累积各档实际计数
    # 用逐步法：状态 = 前 i 个 s、末档 b、七档累计计数 -> 维度过大。
    # 改用「线性规划性质」：L1 目标下逐档计算不可分离，故用带计数的 DP，
    # 计数维度压缩：只需对每个候选切分方案算最终分布。
    # 切分方案数 = C(len(s)+6,6) 量级，s 约 13-37 个值，可接受时直接枚举切分。
    from itertools import combinations_with_replacement
    n = len(s_vals)
    if n > 30:
        raise SystemExit("s 值过多，需换算法")
    # 每个 s 的 delta 直方
    delta_hist = {s: Counter() for s in s_vals}
    for (s, d), c in cnt.items():
        delta_hist[s][d] += c
    # 预计算：base_level[s][b] -> Counter(最终档)
    def final_hist(s, b):
        h = Counter()
        if not bian_on:
            h[b] = delta_hist[s].total()
        else:
            for d, c in delta_hist[s].items():
                h[max(1, min(7, b + d))] += c
        return h
    best = (INF, None)
    # 枚举 6 个切分点（非降），s_vals 有 n 个 → 在 n 个值上放 7 个非降标签
    for cuts in combinations_with_replacement(range(n), 7):
        # cuts[lv] = 该档最后一个 s 值的索引（非降）
        hist = [0] * 7
        for lv in range(7):
            start = 0 if lv == 0 else cuts[lv - 1] + 1
            end = cuts[lv]
            if end < start:
                continue
            for i in range(start, end + 1):
                for f, c in final_hist(s_vals[i], lv + 1).items():
                    hist[f - 1] += c
        dev = sum(abs(hist[i] / total - TARGET[i]) for i in range(7))
        if dev < best[0]:
            best = (dev, cuts, hist)
    return best


def report(name, ws_weight, use_yong_ws, mode):
    cnt = events(ws_weight, use_yong_ws, mode)
    total = sum(cnt.values())
    dev, cuts, hist = dp_optimal(cnt, total, mode != "off")
    s_vals = sorted(set(k[0] for k in cnt), reverse=True)
    print(f"=== {name}  L1总偏差={dev*100:.1f}个百分点  化解触发率(中下+下+下下)={sum(hist[4:])/total*100:.1f}% ===")
    print(f"{'档':<4}{'目标':>6}{'实际':>8}")
    for i in range(7):
        print(f"{LEVELS[i]:<4}{TARGET[i]*100:>5.0f}%{hist[i]/total*100:>7.1f}%")
    mapping = {}
    for lv in range(7):
        start = 0 if lv == 0 else cuts[lv - 1] + 1
        for i in range(start, cuts[lv] + 1):
            mapping[s_vals[i]] = lv + 1
    print("s→档 映射:", ", ".join(f"{s/12:+.2f}→{LEVELS[b-1]}" for s, b in sorted(mapping.items())))
    print()


if __name__ == "__main__":
    report("W1 体卦旺衰+修正全开", 1.0, False, "full")
    report("W2 体卦旺衰无修正", 1.0, False, "off")
    report("W3 体2用1+修正全开", 2 / 3, True, "full")
    report("W4 体2用1+吉不轻破", 2 / 3, True, "asym")
    report("W5 体卦全权重+吉不轻破", 1.0, False, "asym")
