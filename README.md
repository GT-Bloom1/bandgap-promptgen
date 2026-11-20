# 面向 AI4S 科研任务的 Prompt 自动生成：材料文献带隙抽取

硕士课程作业代码仓库。子任务：从材料论文段落中抽取带隙记录（材料、数值、单位、换算后 eV、method、gap_type、证据句）。

## 目录
| 路径 | 内容 |
|---|---|
| `task/schema.yaml` | 组件1 任务形式化：输入/输出/约束/校验规则 |
| `kb/` | 组件2 知识注入：术语表(22条)、方法/类型本体、文献参考带隙表 |
| `src/prompts.py` | 组件3 生成器：模板骨架 + LLM 撰写角色/规则/自检，按组件拼装 |
| `src/optimizer.py` | 组件4 优化闭环：生成→执行→评价→反思→改写(OPRO/TextGrad 风格) |
| `src/verifier.py` | 组件5 验证机制：单位量纲、数值范围、换算一致、证据链、文献值一致性 |
| `src/pipeline.py` | 推理流水线(检索→拼装→调用→校验→失败时带错误信息重试一次) |
| `src/run_experiments.py` | 实验入口(opt / eval / judge) |
| `src/report.py` `src/make_figures.py` `src/analyze.py` | 汇总、图、失败案例 |
| `src/demo.py` | 现场演示脚本(`--demo-id` / `--text` / `--all` / `--extra`) |
| `src/dump_failure_prompts.py` | 导出失败案例当时实际发送的系统提示词和用户消息(`results/failure_prompts.json`),并验证与缓存中的真实请求一致 |
| `src/repro_check.py` | 验证机制的可复现性一项：同一方案重复运行并比较输出一致率 |
| `data/` | `train.jsonl`(26) `test.jsonl`(40) `hard.jsonl`(30) `demo.jsonl`(5)；`build_dataset.py` 为数据源 |
| `prompts/` | 三组方案的 prompt 与优化后的规则 |
| `results/` | 每个配置的逐实例输出、汇总表、显著性、优化轨迹、校验器测试 |
| `cache/` | 全部大模型调用的缓存(可离线复现) |

## 复现
```bash
pip install -r requirements.txt
bash scripts/reproduce.sh          # 默认 OFFLINE=1，命中 cache，不需要 API
```
重新调用大模型：设置 `ANTHROPIC_API_KEY`（及可选 `ANTHROPIC_BASE_URL`），然后 `OFFLINE=0 CLEAR_CACHE=1 bash scripts/reproduce.sh`。模型由环境变量 `TARGET_MODEL` / `OPTIMIZER_MODEL` / `JUDGE_MODEL` 指定，默认均为 `claude-sonnet-5-5`。重新调用得到的数字会因模型非确定性有 1~2 个实例的波动。

## 演示
```bash
python3 src/demo.py --demo-id D01                  # data/demo.jsonl 里的样例
python3 src/demo.py --text "Sb2S3 films show an absorption edge at 885 nm ..."   # 任意新段落
python3 src/demo.py --all                          # 5 条全跑并与标注对照
```
新段落需要真实 API 调用（缓存只覆盖已有输入）。

## 注意（诚实声明）
- 数据集段落由作业作者撰写，数值取自文献常见报道值，不是论文原文摘录；标注由作者按 `task/schema.yaml` 的约定人工确定。
- 目标模型、优化器、评分代理是同一个模型(Sonnet 5.5)。网关里没有 Haiku 4.5。
- “专家评分”在程序里由 LLM 代理给出；`results/human_scoring_sheet.xlsx` 是留给真人评审补充的盲评表。
- 术语表与参考表由作者在看过数据集之后撰写，对测试集存在泄漏风险（见报告第 6 节）。

## 文档
`docs/方案文档.docx`（4 页）、`docs/实验报告.docx`（6 页）、`docs/演示脚本.docx`（5 分钟）；`docs/build_*.js` 为生成脚本。
