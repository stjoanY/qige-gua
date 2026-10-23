# -*- coding: utf-8 -*-
"""
判级矩阵选型 v2（爬山搜索，强制全覆盖——修正 grade_matrix_dp.py 的丢弃缺陷）
================================================================================
背景：grade_matrix_dp.py 的 cuts[6] 可小于 n-1，导致尾部 s 值未分配（最多丢 12% 事件），
     其 W1-W5 结果不可信。本脚本边界变量只定义前 6 档，第 7 档自动延伸到末尾，
     全覆盖无遗漏；对每个变体做多起点爬山搜索求最优「s→基准档」单调分箱。
口径：
  s = 主卦关系分(用生体+2/比和+1/体克用0/体生用-1/用克体-2) + 旺衰项
  旺衰项两种：ti=体卦旺衰值(旺+1/相+0.5/休0/囚-0.5/死-1)
              t2y1=(2×体旺衰值+1×用旺衰值)/3
  变卦修正四种：full=升/降均生效 | asym=升恒生效,降仅主卦分≤0("吉不轻破") |
              up=仅升 | off=无
  最终档 = clamp(基准档 ± 1)，clamp 到 [1,7]。
事件空间：64卦×6动爻×12月支 = 4608 等概率事件（问事签哈希/字数近似均匀的口径）。
"""
import importlib.util
import random
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
                    if ws_mode == "ti":
                        ws = WS_VAL[m.wangshuai_of(ti_wx, mb)]
                    else:
                        ws = (2 * WS_VAL[m.wangshuai_of(ti_wx, mb)]
                              + WS_VAL[m.wangshuai_of(yong_wx, mb)]) / 3
                    delta = 0
                    if corr_mode != "off":
                        if REL_SCORE[rel_bian] > REL_SCORE[rel_main]:
                            delta = -1  # 变卦优于主卦 → 升一档
                        elif REL_SCORE[rel_bian] < REL_SCORE[rel_main]:
                            if corr_mode == "full" or (corr_mode == "asym" and REL_SCORE[rel_main] <= 0):
                                delta = +1  # 劣于主卦 → 降一档
                    s = REL_SCORE[rel_main] + ws
                    cnt[(int(round(scale * s)), delta)] += 1
    return cnt, scale


def hill_climb(cnt, scale, restarts=40, seed=7):
    s_vals = sorted(set(k for k, _ in cnt), reverse=True)  # 高分(吉)在前
    n = len(s_vals)
    dh = {k: Counter() for k in s_vals}
    for (k, d), c in cnt.items():
        dh[k][d] += c
    total = sum(cnt.values())

    def dev_of(bounds):
        """bounds: 6 个非降索引，定义第1-6档的末索引；第7档自动延伸到 n-1（全覆盖）"""
        hist = [0] * 7
        idx = 0
        for j, b in enumerate(bounds):
            for i in range(idx, b + 1):
                base = j + 1
                for d, c in dh[s_vals[i]].items():
                    hist[max(0, min(6, base - 1 + d))] += c
            idx = b + 1
        for i in range(idx, n):
            for d, c in dh[s_vals[i]].items():
                hist[max(0, min(6, 6 + d))] += c
        return sum(abs(hist[i] / total - TARGET[i]) for i in range(7)), hist

    rnd = random.Random(seed)
    best = (float("inf"), None, None)

    for r in range(restarts):
        if r == 0:
            bounds = [max(0, round((n - 1) * (j + 1) / 6) - 1) for j in range(6)]
        else:
            picks = sorted(rnd.sample(range(n), min(6, n)))
            bounds = picks + [n - 1] if False else picks  # 6 个即止
            if len(bounds) < 6:
                continue
        cur_dev, _ = dev_of(bounds)
        improved = True
        while improved:
            improved = False
            for j in range(6):
                for cand in (bounds[j] - 2, bounds[j] - 1, bounds[j] + 1, bounds[j] + 2):
                    if cand < 0 or cand > n - 1:
                        continue
                    if j > 0 and cand < bounds[j - 1]:
                        continue
                    if j < 5 and cand > bounds[j + 1]:
                        continue
                    old = bounds[j]
                    bounds[j] = cand
                    d2, _ = dev_of(bounds)
                    if d2 < cur_dev:
                        cur_dev = d2
                        improved = True
                    else:
                        bounds[j] = old
        if cur_dev < best[0]:
            best = (cur_dev, list(bounds), dev_of(bounds)[1])
    return best, s_vals, total


def mapping_str(bounds, s_vals, scale):
    seg = []
    idx = 0
    for j, b in enumerate(bounds):
        ks = [s_vals[i] for i in range(idx, b + 1)]
        if ks:
            seg.append(f"{LEVELS[j]}:{min(ks)/scale:+.2f}~{max(ks)/scale:+.2f}")
        idx = b + 1
    ks = [s_vals[i] for i in range(idx, n)] if (n := len(s_vals)) and idx < n else []
    if ks:
        seg.append(f"{LEVELS[6]}:{min(ks)/scale:+.2f}~{max(ks)/scale:+.2f}")
    return "; ".join(seg)


if __name__ == "__main__":
    print(f"{'变体':<22}{'最优L1偏差':>10}{'化解率':>8}")
    results = []
    for ws_mode in ("ti", "t2y1"):
        for corr in ("full", "asym", "up", "off"):
            cnt, scale = enum_events(ws_mode, corr)
            (dev, bounds, hist), s_vals, total = hill_climb(cnt, scale)
            hua_lv = sum(hist[4:]) / total
            name = f"{ws_mode}+{corr}"
            results.append((dev, name, ws_mode, corr, bounds, hist, total, s_vals, scale))
            print(f"{name:<22}{dev*100:>9.1f}pct{hua_lv*100:>7.1f}%")
    results.sort(key=lambda x: x[0])
    print()
    for dev, name, ws_mode, corr, bounds, hist, total, s_vals, scale in results:
        print(f"=== {name}  L1={dev*100:.1f}pct  化解率={sum(hist[4:])/total*100:.1f}% ===")
        print(f"{'档':<4}{'目标':>6}{'实际':>8}")
        for i in range(7):
            print(f"{LEVELS[i]:<4}{TARGET[i]*100:>5.0f}%{hist[i]/total*100:>7.1f}%")
        print("分箱:", mapping_str(bounds, s_vals, scale))
        print()
