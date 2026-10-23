# -*- coding: utf-8 -*-
"""
对拍比对器（开发期资产，不进交付物）
====================================
baseline.json（meihua.py 口径） vs conformance.json（index.html 引擎，Node 抽取）
逐字段深度比对：任何类型/数值/字符串不一致都计入 diff。
输出：tests/report.txt（验收证据）
"""
import json

BASE = r"C:\Users\stjoa\WorkBuddy\2026-10-20-17-41-24\qige-gua\tests\baseline.json"
CONF = r"C:\Users\stjoa\WorkBuddy\2026-10-20-17-41-24\qige-gua\tests\conformance.json"
OUT  = r"C:\Users\stjoa\WorkBuddy\2026-10-20-17-41-24\qige-gua\tests\report.txt"

base = json.load(open(BASE, encoding="utf-8"))
conf = json.load(open(CONF, encoding="utf-8"))

lines = []
diffs = []
passed = 0
checked = 0


def deep_diff(path, exp, act):
    """递归比对，返回差异列表。"""
    out = []
    if type(exp) != type(act) and not (isinstance(exp, (int, float)) and isinstance(act, (int, float))):
        out.append("%s 类型不同: expect=%r(%s) actual=%r(%s)" % (path, exp, type(exp).__name__, act, type(act).__name__))
        return out
    if isinstance(exp, dict):
        if not isinstance(act, dict):
            out.append("%s expect=dict actual=%s" % (path, type(act).__name__))
            return out
        for k in exp:
            if k not in act:
                out.append("%s.%s 缺失" % (path, k))
            else:
                out.extend(deep_diff("%s.%s" % (path, k), exp[k], act[k]))
        for k in act:
            if k not in exp:
                out.append("%s.%s 多出" % (path, k))
        return out
    if isinstance(exp, list):
        if not isinstance(act, list) or len(exp) != len(act):
            out.append("%s 列表不等: expect=%r actual=%r" % (path, exp, act))
            return out
        for i, (e, a) in enumerate(zip(exp, act)):
            out.extend(deep_diff("%s[%d]" % (path, i), e, a))
        return out
    if exp != act:
        out.append("%s 不等: expect=%r actual=%r" % (path, exp, act))
    return out


bc, cc = base["cases"], conf["cases"]
ids = sorted(bc.keys())
for cid in ids:
    if cid not in cc:
        diffs.append("[%s] 引擎侧缺失该用例" % cid)
        continue
    checked += 1
    d = deep_diff("[%s]" % cid, bc[cid], cc[cid])
    if d:
        diffs.extend(d)
    else:
        passed += 1

extra = [k for k in cc if k not in bc]
det = conf.get("determinism", {})

lines.append("=== 起个卦 P1.5 灰盒 · 引擎对拍报告 ===")
lines.append("基准: meihua.py（梅花易数参考引擎，只读参照）")
lines.append("被测: index.html §A/§B 引擎（Node 抽取执行）")
lines.append("")
lines.append("用例总数: %d（基准 %d / 引擎 %d）" % (max(len(bc), len(cc)), len(bc), len(cc)))
lines.append("逐字段全等通过: %d / %d" % (passed, checked))
if extra:
    lines.append("引擎侧多出用例: %s" % ",".join(extra))
if diffs:
    lines.append("---- 差异明细（%d 条）----" % len(diffs))
    lines.extend(diffs)
else:
    lines.append("差异明细: 无")
lines.append("")
lines.append("确定性断言（runConformance 内置）:")
for k, v in det.items():
    lines.append("  %s = %s" % (k, v))
det_ok = all(det.get(k) for k in ("twiceByteEqual", "composeByteEqual", "dailySameDayEqual", "askNormalizedEqual"))
lines.append("  确定性总判: %s" % ("PASS" if det_ok else "FAIL"))
lines.append("")
lines.append("结论: %s" % ("对拍全部通过 ✔" if (passed == checked and not diffs and det_ok and not extra) else "存在差异，需修复 ✘"))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("pass %d/%d, diffs=%d, det=%s" % (passed, checked, len(diffs), "OK" if det_ok else "FAIL"))
