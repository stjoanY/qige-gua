# -*- coding: utf-8 -*-
"""
对拍基准生成器（开发期资产，不进交付物）
====================================================
以 meihua.py 为算法口径基准，为 index.html#dev 的 runConformance() 生成 expect。
用例构成（≥30 基准）：
  时间起卦 12（含 23 点换日 2、立春边界 2、2025 闰六月 2）—— 主跑显式指定月支
  节气月支近似路径 4（不显式给月支，验证近似表本身）
  农历↔公历往返 24 + 两端点 2
  数字起卦 8（含 %8==0、%6==0 边界）
  字数起卦 8（plusHour 掺时辰口径 4 + half 前后半拆分口径 4，两口径都要可用）
  直给卦 6（动爻 1-6 各一）
  日柱锚点 2（2000-01-01=戊午、1949-10-01=甲子）
断言前提：所有取模输入恒为正（年支数/字数/农历月日均 ≥1），Python % 与 JS % 无负数分歧。
输出：tests/baseline.json
"""
import importlib.util
import json

SPEC_PATH = r"C:\Users\stjoa\.workbuddy\skills\meihua-yishu\scripts\meihua.py"
spec = importlib.util.spec_from_file_location("meihua", SPEC_PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def pan_subset(r):
    """从 paipan+enrich 全量结果中取对拍字段子集（任务书逐字段口径）。"""
    b, t, a = r["本卦"], r["体用"], r["辅助信息"]

    def gua(x):
        return {"上卦": x["上卦"], "下卦": x["下卦"], "卦名": x["卦名"], "卦序": x["卦序"]}

    return {
        "本卦": gua(b),
        "动爻": r["动爻"],
        "互卦": gua(r["互卦"]),
        "变卦": gua(r["变卦"]),
        "错卦": gua(r["错卦"]),
        "综卦": gua(r["综卦"]),
        "体用": {
            "体卦": t["体卦"], "用卦": t["用卦"],
            "体卦位置": t["体卦位置"], "用卦位置": t["用卦位置"],
            "体卦五行": t["体卦五行"], "用卦五行": t["用卦五行"],
            "变卦用卦": t["变卦用卦"], "变卦用卦五行": t["变卦用卦五行"],
            "主卦关系": t["主卦关系"], "主卦吉凶": t["主卦吉凶"],
            "变卦关系": t["变卦关系"], "变卦吉凶": t["变卦吉凶"],
        },
        "月支": a["月支"], "日柱": a["日柱"], "旬空": a["旬空"],
        "体卦旺衰": a["体卦旺衰"], "用卦旺衰": a["用卦旺衰"],
        "体卦长生": a["体卦长生"], "用卦长生": a["用卦长生"],
        "月德": a["月德"], "驿马": a["驿马"], "桃花": a["桃花"], "日禄": a["日禄"],
        "落空之卦": a["落空之卦"],
    }


def time_case(y, mo, d, hour, mb):
    """时间起卦用例。mb 显式给定（主跑绕开节气近似）；mb=None 时用近似表（a 系列专用）。"""
    ly, lm, ld, is_leap = m.solar_to_lunar(y, mo, d)
    yg, yz = m.year_ganzhi(y, mo, d)
    mb_used = mb if mb else m.solar_month_branch(mo, d)
    jdn = m.jdn_from_gregorian(y, mo, d)
    if hour >= 23:  # 23 点换日（八字惯例，默认口径）
        jdn += 1
    dg, dz = m.day_ganzhi(jdn)
    hg, hz = m.hour_ganzhi(dg, hour)
    mg, _ = m.month_ganzhi(yg, mb_used)
    yb = m.DIZHI.index(yz) + 1
    hb = m.DIZHI.index(hz) + 1
    u, l, mo_v, _ = m.qigua_by_time(yb, lm, ld, hb)
    r = m.enrich(m.paipan(u, l, mo_v), month_branch=mb_used, day_gan=dg, day_zhi=dz)
    return {
        "kind": "time",
        "lunar": [ly, lm, ld, int(is_leap)],
        "year": yg + yz, "month": mg + mb_used, "day": dg + dz, "hour": hg + hz,
        "qigua": [u, l, mo_v],
        "mb": mb_used,
        "pan": pan_subset(r),
    }


def plain_case(u, l, mo, mb, dg, dz):
    """数字/字数/直给卦用例：起卦数已定，直接排盘+enrich。"""
    r = m.enrich(m.paipan(u, l, mo), month_branch=mb, day_gan=dg, day_zhi=dz)
    return {"qigua": [u, l, mo], "pan": pan_subset(r)}


def num_case(nums, mb, dg, dz):
    u, l, mo, _ = m.qigua_by_numbers(nums)
    out = plain_case(u, l, mo, mb, dg, dz)
    out["kind"] = "num"
    return out


def char_plus_hour_case(n, hb, mb, dg, dz):
    """字数掺时辰口径（旧仲裁口径，CONFIG 备用 variant）。"""
    s = n + hb
    u = n % 8 or 8
    l = s % 8 or 8
    mo = s % 6 or 6
    out = plain_case(u, l, mo, mb, dg, dz)
    out["kind"] = "charPlusHour"
    return out


def char_half_case(n, mb, dg, dz):
    """纯字数前后半拆分口径（v1.1 方向；奇数前半多一字，CONFIG 默认）。"""
    a = (n + 1) // 2
    b = n // 2
    u = a % 8 or 8
    l = b % 8 or 8
    mo = n % 6 or 6
    out = plain_case(u, l, mo, mb, dg, dz)
    out["kind"] = "charHalf"
    return out


def hex_case(u, l, mo, mb, dg, dz):
    out = plain_case(u, l, mo, mb, dg, dz)
    out["kind"] = "hex"
    return out


def rt_lunar(ly, lm, ld, is_leap):
    y, mo, d = m.lunar_to_solar(ly, lm, ld, is_leap)
    ly2, lm2, ld2, il2 = m.solar_to_lunar(y, mo, d)
    assert (ly2, lm2, ld2, il2) == (ly, lm, ld, is_leap), "往返不自洽:%r" % ((ly, lm, ld, is_leap),)
    return {"kind": "rt", "solar": [y, mo, d], "lunar": [ly2, lm2, ld2, int(il2)]}


def rt_solar(y, mo, d):
    ly, lm, ld, il = m.solar_to_lunar(y, mo, d)
    y2, mo2, d2 = m.lunar_to_solar(ly, lm, ld, il)
    assert (y2, mo2, d2) == (y, mo, d), "往返不自洽:%r" % ((y, mo, d),)
    return {"kind": "rt", "solar": [y, mo, d], "lunar": [ly, lm, ld, int(il)]}


cases = {}

# ── 时间起卦 12（主跑：月支显式，取真实节气月支） ──
TIME_CASES = [
    ("t01", 2025, 1, 15, 10, "丑"),
    ("t02", 2025, 3, 20, 14, "卯"),
    ("t03", 2025, 4, 8, 6, "辰"),
    ("t04", 2025, 7, 10, 13, "未"),   # 2025 闰六月
    ("t05", 2025, 7, 20, 8, "未"),    # 2025 闰六月
    ("t06", 2026, 2, 3, 12, "丑"),    # 立春边界前
    ("t07", 2026, 2, 5, 12, "寅"),    # 立春边界后
    ("t08", 2026, 5, 12, 18, "巳"),
    ("t09", 2026, 9, 17, 15, "酉"),
    ("t10", 2026, 11, 30, 22, "亥"),  # 23 点换日边界前
    ("t11", 2026, 11, 30, 23, "亥"),  # 23 点换日：日柱进一日
    ("t12", 2026, 12, 21, 0, "子"),   # 早子时
]
for cid, y, mo, d, h, mb in TIME_CASES:
    cases[cid] = time_case(y, mo, d, h, mb)

# ── 节气月支近似路径 4（JS 侧自动推月支，验证近似表逐字节一致） ──
APPROX_CASES = [
    ("a01", 2026, 2, 3, 12),
    ("a02", 2026, 2, 5, 12),
    ("a03", 2025, 6, 6, 9),
    ("a04", 2026, 1, 5, 10),
]
for cid, y, mo, d, h in APPROX_CASES:
    cases[cid] = time_case(y, mo, d, h, None)

# ── 农历↔公历往返 24 + 两端点 ──
RT_LUNAR = [
    ("r01", 2024, 1, 1, False), ("r02", 2024, 4, 1, False),
    ("r03", 2024, 8, 1, False), ("r04", 2024, 12, 1, False),
    ("r05", 2025, 1, 1, False), ("r06", 2025, 6, 1, False),
    ("r07", 2025, 6, 1, True),  # 2025 闰六月初一
    ("r08", 2025, 12, 1, False),
    ("r09", 2026, 1, 1, False), ("r10", 2026, 5, 1, False),
    ("r11", 2026, 9, 1, False), ("r12", 2026, 11, 1, False),
    ("r13", 2000, 1, 1, False), ("r14", 1997, 6, 1, False),
    ("r15", 1949, 10, 1, False), ("r16", 1976, 8, 1, False),
    ("r17", 1901, 3, 1, False), ("r18", 1925, 7, 1, False),
    ("r19", 1958, 2, 1, False), ("r20", 1984, 11, 1, False),
    ("r21", 2038, 1, 1, False), ("r22", 2050, 6, 1, False),
    ("r23", 2077, 4, 1, False), ("r24", 2099, 1, 1, False),
]
for cid, ly, lm, ld, il in RT_LUNAR:
    cases[cid] = rt_lunar(ly, lm, ld, il)
cases["e1"] = rt_solar(1900, 1, 31)   # 表起点：农历 1900 正月初一
cases["e2"] = rt_solar(2100, 12, 31)  # 表终点

# ── 数字起卦 8（三数式；含 %8==0 / %6==0 边界） ──
NUM_CASES = [
    ("n01", [17, 8, 5], "酉", "甲", "子"),
    ("n02", [3, 7, 2], "酉", "甲", "子"),
    ("n03", [8, 16, 6], "酉", "甲", "子"),    # 8%8=0→8, 16%8=0→8, 6%6=0→6 双边界
    ("n04", [24, 32, 12], "酉", "甲", "子"),  # 同上
    ("n05", [1, 1, 1], "寅", "戊", "午"),
    ("n06", [10, 9, 4], "寅", "戊", "午"),
    ("n07", [5, 13, 7], "寅", "戊", "午"),
    ("n08", [9, 18, 6], "寅", "戊", "午"),    # 18%8=2, 6%6=0→6
]
for cid, nums, mb, dg, dz in NUM_CASES:
    cases[cid] = num_case(nums, mb, dg, dz)

# ── 字数起卦 8（两口径都验：掺时辰 4 + 前后半拆分 4） ──
CHAR_PH = [
    ("c01", 5, 7), ("c02", 8, 3), ("c03", 16, 7), ("c04", 1, 1),
]
for cid, n, hb in CHAR_PH:
    cases[cid] = char_plus_hour_case(n, hb, "酉", "甲", "子")
CHAR_HALF = [
    ("d01", 5), ("d02", 8), ("d03", 1), ("d04", 16),
]
for cid, n in CHAR_HALF:
    cases[cid] = char_half_case(n, "酉", "甲", "子")

# ── 直给卦 6（动爻 1-6 各一，体用定位两种位置全覆盖） ──
HEX_CASES = [
    ("h01", 1, 8, 1, "酉", "甲", "子"),
    ("h02", 3, 6, 2, "酉", "甲", "子"),
    ("h03", 5, 5, 3, "酉", "甲", "子"),
    ("h04", 2, 7, 4, "寅", "戊", "午"),
    ("h05", 8, 2, 5, "寅", "戊", "午"),
    ("h06", 6, 4, 6, "寅", "戊", "午"),
]
for cid, u, l, mo, mb, dg, dz in HEX_CASES:
    cases[cid] = hex_case(u, l, mo, mb, dg, dz)

# ── 日柱锚点 2 ──
cases["k1"] = {"kind": "anchor", "dayGanzhi": "".join(m.day_ganzhi(m.jdn_from_gregorian(2000, 1, 1)))}
cases["k2"] = {"kind": "anchor", "dayGanzhi": "".join(m.day_ganzhi(m.jdn_from_gregorian(1949, 10, 1)))}

out = {
    "note": "起个卦 P1.5 对拍基准 · meihua.py 口径 · 主跑月支显式（t 系），近似路径 a 系列",
    "count": len(cases),
    "cases": cases,
}
with open(r"C:\Users\stjoa\WorkBuddy\2026-10-20-17-41-24\qige-gua\tests\baseline.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("baseline cases:", len(cases))
