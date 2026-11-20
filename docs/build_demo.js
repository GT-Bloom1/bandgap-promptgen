const L = require('./lib.js');
const { P, H1, H2, B, N, CAP, NOTE, table, mkdoc, save, ROOT, AlignmentType, Paragraph, TextRun } = L;
const c = [];
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new TextRun({ text: '现场演示脚本（5 分钟）', font: 'SimHei', size: 34, bold: true, color: '1F3864' })] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 140 }, children: [new TextRun({ text: '材料文献带隙抽取的 Prompt 自动生成   撰写：ClawsGO Science Agent', font: 'SimSun', size: 18, color: '555555' })] }));
c.push(H1('1  演前检查'));
c.push(B('终端进入仓库根目录，确认 `python3 src/demo.py --demo-id D01` 能跑通（会访问大模型接口，需要网络和 `ANTHROPIC_API_KEY`；`--demo-id` 对应的 5 条样例有缓存，离线也能跑）。'));
c.push(B('提前打开三份材料：`figures/fig_pipeline.png`（流程图）、`prompts/std_kb_optimized_spec.json`（优化后的规则）、`results/table_main.csv`（结果表）。'));
c.push(B('让老师现场给一段新文本时，用 `python3 src/demo.py --text "..."`，这一步必须联网。联网失败时改用 `--demo-id D05`（演示集中此前从未使用过的样例），并如实说明。'));
c.push(H1('2  时间安排'));
c.push(table(['时间', '内容', '操作', '要点'], [
  ['0:00–0:40', '任务与难点', '展示一段含 PBE 值、HSE 值、引用值、nm 吸收边的段落', '同一个 band gap 有光学/电子之分；引用值、单位、范围会让人工 prompt 出错。A 的准确率 67.1%，格式合规率只有 55.7%。'],
  ['0:40–1:50', '方案五组件', '指着流程图从上到下讲', '① schema 同时驱动提示与校验；② 术语表 + 示例检索；③ 模板 + LLM 生成规则；④ 失败样例驱动的改写闭环；⑤ 单位、范围、证据链、文献值校验。'],
  ['1:50–3:40', '现场运行未见样例', '`python3 src/demo.py --demo-id D05`，再用老师给的新段落运行 `--text`', '指出三处：检索到的术语条目和示例；输出里 255/320 nm 被换算成 eV；校验报告中 evidence 为原文子串。出错时就讲错在哪一步。'],
  ['3:40–4:30', '实验结果', '展示 `results/table_main.csv` 与消融图', '本方案 94.3% 对 A 67.1%、B 62.9%（+27/+31 个百分点，p<0.001）；A2 98.6% 说明提升主要来自 schema；知识注入与闭环在标准设置下没有测得收益，冷启动下闭环 +5.7 个百分点但不显著。'],
  ['4:30–5:00', '失败与局限', '展示报告第 7 节的案例表', '数据由作者撰写、模型单一偏强、专家评分是 LLM 代理；本方案自身的错误集中在并列分句的技术沿用和对照值误收。'],
], [1100, 1500, 3100, 3938], { size: 17 }));
c.push(H1('3  预期输出与应对'));
c.push(table(['场景', '预期', '应对'], [
  ['D05：LiNbO3，320 nm 吸收边 + GGA+U 3.5 eV + 文献 3.9 eV', '输出 2 条：实验 3.875 eV（optical）、DFT 3.5 eV（electronic）；文献 3.9 eV 不收', '可点出校验器报告 errors=[]、warnings=[]。'],
  ['D04：WS2 单层，STS 2.4 eV 与吸收 2.0 eV', '2 条记录，分别为 electronic 与 optical', '用来说明光学带隙与电子带隙的区别。'],
  ['老师给的新段落', '运行一次约 10–30 秒', '接口超时就再试一次；仍失败则切换到 D05 并说明原因。'],
  ['输出与老师预期不一致', '——', '先看 evidence 字段对应的原文，再说明是模型错误、标注约定还是术语歧义；不要临时改 prompt。'],
], [3300, 3500, 2838], { size: 17 }));
c.push(NOTE('演示集 D01–D05 共 8 条记录，从未参与优化与评测；在当前方案下 5 条全部与标注一致（见 `results/demo_outputs.json`）。这只是 5 条样例，不能当作泛化证据。'));
save(mkdoc(c, '演示脚本'), ROOT + '/docs/演示脚本.docx');
