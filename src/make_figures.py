"""生成报告用图：流程图、主结果、消融、优化收敛。"""
import json, os, random, subprocess, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures"); os.makedirs(FIG, exist_ok=True)
S = json.load(open(os.path.join(ROOT, "results", "summary.json")))
rows = json.load(open(os.path.join(ROOT, "results", "eval_rows.json")))
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
random.seed(0)

DOT = r'''
digraph G {
  rankdir=TB; fontname="Noto Sans CJK SC"; nodesep=0.3; ranksep=0.5; newrank=true;
  node [shape=box, style="rounded,filled", fontname="Noto Sans CJK SC", fontsize=13, fillcolor="#EAF2FB", color="#4A7DB5", margin="0.15,0.08"];
  edge [fontname="Noto Sans CJK SC", fontsize=11, color="#555555"];
  subgraph cluster_off { label="离线：构建与优化(一次性)"; fontsize=14; fontname="Noto Sans CJK SC"; style=dashed; color="#999999";
    schema [label="① 任务形式化\nschema.yaml\n输入/输出/约束/校验", fillcolor="#FFF2CC", color="#BF9000"];
    kb [label="② 知识库\n术语表22条·本体\n示例库(训练集26条)", fillcolor="#FFF2CC", color="#BF9000"];
    gen [label="③ 生成器\n模板骨架 + LLM 撰写\n角色/规则/自检"];
    exe [label="执行\n目标模型\n(留一检索)"];
    ev  [label="评价\n与标注比对\n准确率/记录级F1"];
    ref [label="反思\n失败样例作文本梯度\n优化器LLM改写规则"];
    pick[label="选优\n每轮3候选，训练集\n打分，无提升早停"];
    {rank=same; schema; kb; gen}
    {rank=same; exe; ev; ref; pick}
    schema -> gen; kb -> gen [style=dotted]; gen -> exe; exe -> ev -> ref -> pick; pick -> exe [label="④ 下一轮", style=dashed, constraint=false];
  }
  subgraph cluster_on { label="在线：每条输入的推理"; fontsize=14; fontname="Noto Sans CJK SC"; style=dashed; color="#999999";
    inp [label="论文段落", shape=note, fillcolor="#FFFFFF"];
    ret [label="检索\n术语表(关键词)\n示例(TF-IDF top-3)"];
    asm [label="拼装 prompt\n优化后的规则+schema\n+知识+示例+自检"];
    llm [label="目标 LLM", fillcolor="#E2F0D9", color="#548235"];
    ver [label="⑤ 校验器\n单位量纲·数值范围\n换算一致·证据链·文献值", fillcolor="#FCE4D6", color="#C55A11"];
    out [label="结构化 JSON\n+ 校验报告", shape=note, fillcolor="#FFFFFF"];
    {rank=same; inp; ret; asm}
    {rank=same; llm; ver; out}
    inp -> ret -> asm; asm -> llm -> ver; ver -> out [label="通过"]; ver -> asm [label="失败：带错误信息重试1次", style=dashed, color="#C55A11", constraint=false];
  }
  pick -> asm [label="最优规则", style=bold, color="#4A7DB5"];
}
'''
open(os.path.join(FIG, "pipeline.dot"), "w").write(DOT)
subprocess.run(["dot", "-Tpng", "-Gdpi=170", os.path.join(FIG, "pipeline.dot"), "-o", os.path.join(FIG, "fig_pipeline.png")], check=True)


def boot_ci(cfg, key="exact", B=3000):
    x = [r[key] for r in rows[cfg]]; n = len(x)
    m = sorted(sum(x[random.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return m[int(.025 * B)], m[int(.975 * B)]


# 主结果
cfgs = ["A_manual", "B_direct_llm", "OURS", "A2_manual_schema"]
lab = ["A 人工\nprompt", "B 直接由\nLLM 生成", "本方案", "A2 人工+schema\n(参考上界)"]
fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
w = 0.27
for k, (split, c) in enumerate((("test", "#9DC3E6"), ("hard", "#F4B183"), ("all", "#2E75B6"))):
    ys = [S[c_][split]["acc"] for c_ in cfgs]
    ax[0].bar([i + (k - 1) * w for i in range(4)], ys, w, label={"test": "Test-40", "hard": "Hard-30", "all": "合计 70"}[split], color=c)
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(lab, fontsize=8); ax[0].set_ylim(0, 1.08); ax[0].set_ylabel("实例级准确率(严格)"); ax[0].legend(fontsize=8, loc="lower right")
fm = [S[c_]["all"]["fmt"] for c_ in cfgs]
ax[1].bar(range(4), fm, color=["#9DC3E6", "#9DC3E6", "#2E75B6", "#9DC3E6"]); ax[1].set_xticks(range(4)); ax[1].set_xticklabels(lab, fontsize=8); ax[1].set_ylim(0, 1.08); ax[1].set_ylabel("格式合规率(严格 JSON)")
tk = [S[c_]["all"]["tokens"] for c_ in cfgs]
ax[2].bar(range(4), tk, color=["#9DC3E6", "#9DC3E6", "#2E75B6", "#9DC3E6"]); ax[2].set_xticks(range(4)); ax[2].set_xticklabels(lab, fontsize=8); ax[2].set_ylabel("平均 token / 实例")
for a_, v in zip(ax[1:], (fm, tk)):
    for i, y in enumerate(v): a_.text(i, y, f"{y:.2f}" if y <= 1 else f"{y:.0f}", ha="center", va="bottom", fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_main.png"), dpi=170); plt.close()

# 消融
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
std = [("OURS", "完整"), ("OURS_noKB", "- 知识注入"), ("OURS_noLoop", "- 优化闭环"), ("OURS_noRepair", "- 校验修复")]
cold = [("COLD_gen_only", "仅生成器"), ("COLD_KB", "+ 知识注入"), ("COLD_loop", "+ 优化闭环"), ("COLD_full", "完整")]
for a_, grp, title in ((ax[0], std, "标准设置(schema 含约束)"), (ax[1], cold, "冷启动设置(schema 不含约束)")):
    ys = [S[c]["all"]["acc"] for c, _ in grp]; cis = [boot_ci(c) for c, _ in grp]
    err = [[y - c[0] for y, c in zip(ys, cis)], [c[1] - y for y, c in zip(ys, cis)]]
    a_.bar(range(4), ys, color=["#2E75B6", "#9DC3E6", "#9DC3E6", "#9DC3E6"], yerr=err, capsize=4)
    for i, y in enumerate(ys): a_.text(i, 0.76, f"{y:.3f}", ha="center", fontsize=9, color="white" if False else "black")
    a_.set_xticks(range(4)); a_.set_xticklabels([l for _, l in grp]); a_.set_ylim(0.75, 1.03); a_.set_title(title, fontsize=10); a_.set_ylabel("严格准确率 (70条, 95% CI)")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_ablation.png"), dpi=170); plt.close()

# 优化收敛
fig, ax = plt.subplots(figsize=(5.2, 3.4))
names = {"std_kb": "标准+知识", "std_nokb": "标准, 无知识", "cold_kb": "冷启动+知识", "cold_nokb": "冷启动, 无知识"}
for n, c in zip(names, ["#2E75B6", "#9DC3E6", "#C55A11", "#F4B183"]):
    t = json.load(open(os.path.join(ROOT, "results", f"opt_trace_{n}.json")))["trace"]
    xs, ys, best = [], [], 0
    for r in t:
        best = max(best, r["score"]) if r["kind"] != "rejected" else best
        xs.append(r["round"]); ys.append(best)
    ax.plot(xs, ys, "o-", color=c, label=names[n])
ax.set_xlabel("优化轮次"); ax.set_ylabel("训练集得分 (准确率+F1)/2"); ax.set_ylim(0.9, 1.01); ax.set_xticks(range(0, 3)); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig_opt.png"), dpi=170); plt.close()
print("figures ok")
