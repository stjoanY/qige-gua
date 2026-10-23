// 对拍运行器（开发期资产，不进交付物）
// 用法：node extract_run.js <index.html路径> <输出json路径>
// 从 index.html 抠出唯一 <script> 段，在 Node 全局环境执行（HAS_DOM=false 跳过 UI 初始化），
// 调 runConformance() 落盘 JSON，交 compare.py 与 baseline.json 逐字段比对。
"use strict";
const fs = require("fs");
const htmlPath = process.argv[2] || "C:/Users/stjoa/WorkBuddy/2026-10-20-17-41-24/qige-gua/index.html";
const outPath = process.argv[3] || "C:/Users/stjoa/WorkBuddy/2026-10-20-17-41-24/qige-gua/tests/conformance.json";

const html = fs.readFileSync(htmlPath, "utf8");
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error("FATAL: 未找到 <script> 段"); process.exit(1); }

const code = m[1];
try {
  (0, eval)(code); // 间接 eval → 全局作用域；脚本自身为 IIFE，仅在 globalThis 上挂 __QG__
} catch (e) {
  console.error("FATAL: 脚本执行异常:", e && e.stack || e);
  process.exit(1);
}
if (!globalThis.__QG__ || typeof globalThis.__QG__.runConformance !== "function") {
  console.error("FATAL: __QG__.runConformance 未导出");
  process.exit(1);
}
const res = globalThis.__QG__.runConformance();
fs.writeFileSync(outPath, JSON.stringify(res, null, 1), "utf8");
console.log("OK cases=" + res.count + " determinism=" + JSON.stringify(res.determinism));
