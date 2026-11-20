const L = require('./lib.js');
const fs = require('fs');
const { P, H1, H2, B, N, CAP, NOTE, table, img, SP, mkdoc, save, S, VT, f3, pt, ROOT, AlignmentType, Paragraph, TextRun } = L;
const sig = S._significance;
const g = (k) => S[k].all;
const OT = {}; for (const n of ['std_kb', 'std_nokb', 'cold_kb', 'cold_nokb']) OT[n] = JSON.parse(fs.readFileSync(`${ROOT}/results/opt_trace_${n}.json`, 'utf8'));
const sgn = (x) => (x >= 0 ? '+' : '') + (x * 100).toFixed(1);
const sigRow = (key, label) => { const v = sig[key].exact; return [label, `${sgn(v.diff)}`, `[${sgn(v.ci[0])}, ${sgn(v.ci[1])}]`, `${v.a_only} / ${v.b_only}`, v.p < 0.001 ? '<0.001' : v.p.toFixed(3)]; };
const c = [];
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new TextRun({ text: '实验报告：材料文献带隙抽取的 Prompt 自动生成', font: 'SimHei', size: 34, bold: true, color: '1F3864' })] }));
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 140 }, children: [new TextRun({ text: '姓名/学号：__________   2026-11-05   撰写：ClawsGO Science Agent', font: 'SimSun', size: 18, color: '555555' })] }));

c.push(H1('1  结论摘要'));
c.push(B(`**自动方案明显优于两种常见做法。** 在 70 条测试实例上，实例级严格准确率：本方案 ${pt(g('OURS').acc)}%，人工 prompt A ${pt(g('A_manual').acc)}%，直接由 LLM 生成的 B ${pt(g('B_direct_llm').acc)}%；相对 A、B 分别提高 ${sgn(sig['OURS vs A_manual'].exact.diff)}、${sgn(sig['OURS vs B_direct_llm'].exact.diff)} 个百分点（配对 bootstrap 95% CI 不含 0，McNemar p<0.001）。严格 JSON 合规率 100%，A 为 ${pt(g('A_manual').fmt)}%。`));
c.push(B(`**提升主要来自任务形式化。** 只给人工 prompt 补上 schema 的字段说明与 6 条约束（A2），准确率就达到 ${pt(g('A2_manual_schema').acc)}%，与本方案（${pt(g('OURS').acc)}%）无显著差异（p=${sig['OURS vs A2_manual_schema'].exact.p.toFixed(3)}）。本方案的好处是格式 100% 合规、规则可自动重新生成，并非准确率更高。`));
c.push(B(`**消融结果与预期不同。** 标准设置下去掉知识注入后严格准确率从 ${pt(g('OURS').acc)}% 变为 ${pt(g('OURS_noKB').acc)}%（没有下降，反而 ${sgn(g('OURS_noKB').acc - g('OURS').acc)} 个百分点，不显著），token 成本却少 34%；去掉优化闭环或校验修复，准确率不变。冷启动设置（schema 不含约束）下，闭环把 ${pt(g('COLD_gen_only').acc)}% 提高到 ${pt(g('COLD_loop').acc)}%（${sgn(g('COLD_loop').acc - g('COLD_gen_only').acc)} 个百分点，p=${sig['COLD_loop vs COLD_gen_only'].exact.p.toFixed(3)}，不显著）。`));
c.push(B(`**校验器本身有效，但在这批输出上没有触发。** 对 101 条人工标注答案误报 0 条；对注入的错误，换算错误、数量级错误、证据链断裂、枚举非法的检出率均为 100%，单位误标 80%，与文献值明显不符 ${pt(VT.detection.wrong_value_vs_ref.rate)}%。70 条真实输出中它触发 0 次，所以“校验修复”这项的贡献为 0。`));
c.push(B('**统计功效有限。** 70 条实例只能分辨约 10 个百分点以上的差异；±4 个百分点以内的差别属于噪声（改动一条示例的证据字段后重跑，就有一条实例的输出发生变化）。'));

c.push(H1('2  数据与设置（要点）'));
c.push(P('完整设置见第一部分（方案文档）第 3 节。这里只列和解读结果有关的几点：测试实例共 70 条（test 40 + hard 30），标注记录 104 条；优化闭环只使用 26 条训练实例，few-shot 示例库也只来自这 26 条，测试实例不参与任何优化或检索。目标模型为 Claude Sonnet 5.5，温度 0。作业建议的 Haiku 4.5 在本环境的模型网关里不可用，本地也没有可运行的开源模型，所以全部环节用同一个模型；已知其能力强，使不同方案的差距被压缩。'));

c.push(H1('3  主结果'));
c.push(CAP('表 3  三组方案与参考上界（70 条测试实例）'));
const mrow = (k, name) => { const a = g(k); return [name, pt(S[k].test.acc), pt(S[k].hard.acc), pt(a.acc), pt(a.acc_nm), pt(a.f1), pt(a.fmt), a.judge ? a.judge.toFixed(2) : '-', Math.round(a.tokens)]; };
c.push(table(['方案', 'Test-40\n准确率%', 'Hard-30\n准确率%', '合计 70\n准确率%', '名称无关\n准确率%', '记录级\nF1 %', '格式\n合规率%', '评分\n代理(1-5)', 'token\n/实例'],
  [mrow('A_manual', 'A 人工 prompt'), mrow('B_direct_llm', 'B 直接由 LLM 生成'), mrow('A2_manual_schema', 'A2 人工+完整 schema（参考上界）'), mrow('OURS', '本方案（完整）')],
  [2400, 800, 800, 900, 900, 800, 800, 1000, 1238], { size: 17, alignNum: true, hl: (i) => i === 3 }));
c.push(NOTE('准确率为严格口径：该实例所有记录的材料、数值、method、gap_type 都对且无多余记录。名称无关口径不比较材料名写法。评分代理是 LLM 评审，不是真人专家（见第 8 节）。'));
c.push(img(ROOT + '/figures/fig_main.png', 9200));
c.push(CAP('图 2  主结果：准确率（左）、格式合规率（中）、平均 token（右）'));
c.push(P(`两个观察。第一，A 与 B 在 hard 和 test 上互有胜负（A：${pt(S.A_manual.test.acc)}%/${pt(S.A_manual.hard.acc)}%；B：${pt(S.B_direct_llm.test.acc)}%/${pt(S.B_direct_llm.hard.acc)}%），说明“让 LLM 写 prompt”本身没有系统性优势；B 的 prompt 用了“禁止代码围栏”所以格式合规，但它主动要求抽取引用文献中的数值，与本任务的标注约定冲突。第二，LLM 评分代理给 A 和 B 都是 4.43，几乎不能区分它们，而严格准确率相差 4 个百分点、A 与本方案相差 27 个百分点；评分代理偏宽松，不能当作真人专家评分的替代。`));

c.push(H1('4  消融实验'));
c.push(CAP('表 4  消融（70 条测试实例，严格准确率）'));
const arow = (k, name, ref) => { const a = g(k); const d = ref == null ? '-' : sgn(a.acc - ref); return [name, pt(a.acc), d, pt(a.f1), Math.round(a.tokens)]; };
c.push(table(['配置', '准确率 %', '相对参照\n(百分点)', '记录级\nF1 %', 'token\n/实例'], [
  ['**标准设置：参照 = 本方案完整**', '', '', '', ''],
  arow('OURS', '本方案（完整）', null),
  arow('OURS_noKB', '- 知识注入（无术语表、无 few-shot）', g('OURS').acc),
  arow('OURS_noLoop', '- 优化闭环（用生成器初始规则）', g('OURS').acc),
  arow('OURS_noRepair', '- 校验修复', g('OURS').acc),
  ['**冷启动设置：schema 不含抽取约束；参照 = 冷启动完整**', '', '', '', ''],
  arow('COLD_full', '冷启动完整（闭环 + 知识 + 修复）', null),
  arow('COLD_loop', '- 知识注入（仅闭环）', g('COLD_full').acc),
  arow('COLD_KB', '- 优化闭环（仅知识注入）', g('COLD_full').acc),
  arow('COLD_gen_only', '- 闭环与知识（仅生成器）', g('COLD_full').acc),
  arow('COLD_full_noRepair', '- 校验修复', g('COLD_full').acc),
], [4300, 1100, 1300, 1300, 1638], { size: 17, alignNum: true }));
c.push(img(ROOT + '/figures/fig_ablation.png', 8600));
c.push(CAP('图 3  消融（误差线为 95% bootstrap 置信区间）'));
c.push(P(`**知识注入。** 标准设置下去掉后没有下降（${sgn(g('OURS_noKB').acc - g('OURS').acc)} 个百分点），平均 token 从 ${Math.round(g('OURS').tokens)} 降到 ${Math.round(g('OURS_noKB').tokens)}。原因是 schema 已把大部分术语约定写进了规则，剩下的少数差异（如 X66 漏掉 mBJ 计算值）和术语表引入的干扰（如 X18 把体相硅的对照值当成本文结果）互相抵消。冷启动下去掉知识注入反而升高 ${sgn(g('COLD_loop').acc - g('COLD_full').acc)} 个百分点。结论：在这个任务、这个模型上，知识注入没有测得收益。`));
c.push(P(`**优化闭环。** 标准设置下训练集初始得分 0.942，一轮优化即满分（${OT.std_kb.opt_calls} 次模型调用、${(OT.std_kb.opt_tokens / 1000).toFixed(0)}k token），测试集上与不优化相比准确率相同（${pt(g('OURS').acc)}%）。冷启动下去掉闭环让准确率降 ${(-(g('COLD_KB').acc - g('COLD_full').acc) * 100).toFixed(1)} 个百分点，去掉闭环与知识让它降 ${(-(g('COLD_gen_only').acc - g('COLD_full').acc) * 100).toFixed(1)} 个百分点，方向与预期一致，但样本量下 p>0.2。`));
c.push(P('**校验修复。** 两种设置下都是 0.0 个百分点，因为校验器在 70 条真实输出上一次都没有触发，原因见第 6.2 节。'));

c.push(H1('5  显著性检验'));
c.push(CAP('表 5  配对比较（实例级严格准确率）'));
c.push(table(['比较（前者 − 后者）', '差值\n(百分点)', '95% bootstrap CI', '前者对/后者错\n:前者错/后者对', 'McNemar p'], [
  sigRow('OURS vs A_manual', '本方案 − A 人工'), sigRow('OURS vs B_direct_llm', '本方案 − B 直接生成'), sigRow('OURS vs A2_manual_schema', '本方案 − A2 人工+schema'),
  sigRow('OURS vs OURS_noKB', '本方案 − 去知识注入'), sigRow('OURS vs OURS_noLoop', '本方案 − 去优化闭环'),
  sigRow('COLD_full vs COLD_gen_only', '冷启动完整 − 仅生成器'), sigRow('COLD_loop vs COLD_gen_only', '冷启动仅闭环 − 仅生成器'), sigRow('COLD_KB vs COLD_gen_only', '冷启动仅知识 − 仅生成器'),
], [3200, 1100, 2200, 1900, 1238], { size: 17, alignNum: true }));
c.push(NOTE('只有“本方案 vs A、B”两行的置信区间不含 0。其余差异都落在噪声范围内，不能据此判断组件有没有用。'));

c.push(H1('6  优化闭环与校验器的行为'));
c.push(H2('6.1  闭环做了什么'));
c.push(CAP('表 6  四次优化运行（训练集 26 条）'));
const orow = (n, name) => { const t = OT[n].trace; return [name, t.map((x) => x.score.toFixed(3)).join(' → '), t.length - 1, OT[n].opt_calls, Math.round(OT[n].opt_tokens / 1000) + 'k']; };
c.push(table(['运行', '训练集得分轨迹（每轮最优候选）', '轮数', '模型调用', '优化 token'], [orow('std_kb', '标准 + 知识'), orow('std_nokb', '标准，无知识'), orow('cold_kb', '冷启动 + 知识'), orow('cold_nokb', '冷启动，无知识')], [2300, 3500, 800, 1300, 1738], { size: 17, alignNum: true }));
c.push(P('反思器从失败样例中归纳出的规则，与人工在 schema 里写的约束是同一类：(1) “只给吸收边或截止波长的值要换算成 eV 并记录”；(2) “汇总性的范围不收，只收落在具体样品或条件上的端点”；(3) “不收基线值、数据库值和仅作对照的值”；(4) “材料字段只写原文出现过的条件，避免冗长或臆测的标注”。冷启动无知识运行从 0.917 提高到 1.000，说明在 schema 不含约束时闭环能自己补上其中大部分。但有一条学到的规则过窄，见失败案例 5。'));
c.push(img(ROOT + '/figures/fig_opt.png', 5200));
c.push(CAP('图 4  训练集得分随优化轮次的变化'));
c.push(H2('6.2  校验器的评测'));
c.push(P('校验器用两种方式评测，都不调用大模型。(1) 误报：对全部 101 条人工标注答案运行，0 条被误报。(2) 注入错误：对每条标注记录做一种破坏，看是否检出。'));
c.push(CAP('表 7  校验器注入错误检出率'));
const nm = { unit_as_ev: '单位误标：nm 数值写成 eV', bad_conversion: '换算错误：eV 值乘 1.5', out_of_range: '数量级错误：放大 100 倍', evidence_fabricated: '证据链断裂：证据不是原文子串', bad_enum: '枚举非法：method 不在集合内', wrong_value_vs_ref: '与文献值明显不符：数值乘 3，量纲合法' };
c.push(table(['注入的错误', '样本数', '检出', '检出率'], Object.entries(VT.detection).map(([k, v]) => [nm[k], v.n, v.detected, pt(v.rate) + '%']), [5200, 1300, 1300, 1838], { size: 17, alignNum: true }));
c.push(P('70 条真实输出里没有一条违反这些检查：在 schema 与自检提示下，模型已能正确换算单位、引用原文，参考表覆盖的材料数值也都落在范围内，所以重试从未被触发。两点局限。文献值核查只能覆盖参考表里的 48 种体相材料，并且范围取得宽，所以对“数值乘 3”这类错误只检出一半多；单位误标漏检的三条都是 µm 数值（1.65、10.2、4.5），数值本身落在 0–15 内，又不在参考表里。校验器开发过程中发现并修正了两处缺陷：参考表原先按子串匹配，把 SnS2 误配成 SnS、把 silicon 误配成 Si；量子点、纳米结构和非晶样品的带隙本来就偏离体相值，现在跳过文献值核查。这两处修正是看到评测输出里的误报之后做的，修正后重跑了全部评测，没有改变任何实例的结论。'));
c.push(...require('./extra_sections.js')(L));

c.push(H1('7  失败案例分析'));
c.push(P('下表列出七个真实失败案例，覆盖本方案、两个消融变体和参考上界 A2。前四个是本方案自身的错误。'));
c.push(table(['#', '配置 / 实例', '原文要点', '模型输出与金标准', '原因与归类'], [
  ['1', '本方案\nX07', 'Bulk g-C3N4 的 2.70 eV 来自 UV-vis 漫反射；“exfoliated nanosheets 的 2.88 eV”', '体相标为 optical（对）；纳米片标为 unspecified，金标准是 optical', '**模型错误。** 测试技术写在前半句，后半句用“whereas”并列，模型没有把技术沿用过去。属于上下文共指，规则已写“未说明获取方式时才用 unspecified”，但对并列句判断偏保守。'],
  ['2', '本方案\nX52', '异质结 Tauc 带隙 2.95 eV，“between the 3.20 eV of pure TiO2 and 2.70 eV of pure g-C3N4 measured under identical conditions”', '纯 TiO2、纯 g-C3N4 标为 unspecified，金标准是 optical', '**标注与保守策略的分歧。** 原文没有逐一写明技术，金标准是我按“同条件测得”推断的。模型的保守选择有合理性，这条标注可争议。'],
  ['3', '本方案\nX11、X38', 'X11：AlxGa1-xN，x=0.2 / 0.4；X38：紧束缚计算的氢钝化硅量子点', '数值、method、gap_type 全部正确；材料名写成 “AlxGa1-xN (x = 0.2)”“hydrogen-terminated silicon quantum dots”，金标准是 Al0.2Ga0.8N、Si quantum dot', '**评分器局限。** 严格口径按材料名匹配，这两条被判错；名称无关口径下判对。这是严格准确率比名称无关低 2.8 个百分点的来源。'],
  ['4', '本方案-知识注入\nX66', 'mBJ 势计算 SrTiO3 带隙 3.2 eV；STS 实测 3.3 eV', '只输出了 STS 的 3.3 eV，漏掉 mBJ 的 3.2 eV', '**召回失败。** 没有术语表，模型没有把 “Tran-Blaha modified Becke-Johnson” 识别为 DFT 方法。这是知识注入在本实验里唯一能明确归因的作用。'],
  ['5', '冷启动-知识注入\n仅闭环 X19', 'β-Ga2O3 “absorption edge at 255 nm”；HSE06 计算 4.78 eV', '只输出了 HSE06 的 4.78 eV，漏掉 255 nm 吸收边', '**过拟合的学到规则。** 闭环写出的规则要求原文说明“带隙由吸收边估计”，而这段话只写了吸收边的位置。规则对训练集有效，对测试集过窄。'],
  ['6', '冷启动-闭环\n仅知识注入 X18', 'STS 测得 Si 纳米线带隙 1.3 eV；“Bulk silicon has a gap of 1.12 eV”', '多输出一条 Si (bulk) 1.12 eV，标为 experimental', '**干扰值误收。** 对照用的体相值被当成本文结果。术语表条目并不阻止这种误判，说明关键词检索给出的提示粒度太粗。'],
  ['7', 'A2（人工+schema）\nX41', '“band gaps ranging from 1.73 to 2.31 eV. The x = 0.5 film has a Tauc gap of 1.95 eV”', '把范围的两端各输出一条，金标准只有 1.95 eV', '**标注约定缺失。** A2 的 schema 里没有范围规则；本方案的生成器和闭环都写入了范围规则，通过了这条。'],
], [400, 1300, 2500, 2500, 2938], { size: 16 }));
c.push(SP());
c.push(P('案例 3 之外，其余失败都是真实的内容错误。它们集中在三类：并列分句的技术沿用（1）、原文未显式给出信息时的推断边界（2、5）、对照值与本文结果的区分（6）。前者需要更长的上下文推理，后两者是标注约定，换更强的模型不一定能解决。'));

c.push(H1('8  局限与有效性威胁'));
c.push(B('**数据由作者撰写。** 70 条测试段落不是论文原文，是按文献常见值写的，标注者也是方案设计者。真实论文的杂乱程度会更高，绝对准确率会偏高估计；方案之间的相对比较不受这一点直接影响。'));
c.push(B('**知识库对测试集有泄漏风险。** 术语表与参考表是在看过数据集之后写的。我已删去与单个测试实例过于对应的条目，但无法排除泄漏。消融显示知识注入没有带来增益，这个风险没有转化为方案的优势。'));
c.push(B('**模型单一，且偏强。** 目标、优化器、评分代理是同一个模型，评分代理对同源输出可能偏宽（A、B 都得 4.43）。A2 已达 98.6%，天花板效应压缩了组件之间的差距。若换成能力更弱的模型，知识注入和闭环可能有更大作用，这一点本实验没有验证。'));
c.push(B('**专家评分未由真人完成。** 表中的评分是 LLM 代理给出的。`results/human_scoring_sheet.xlsx` 是 20 条实例 × 3 个方案的盲评表，评审人填完后即可补上真人评分。'));
c.push(B('**事后改动。** 名称无关口径与校验器的两处修正是在看到结果后加入或做出的，已在正文逐一说明；主口径仍是预先定义的严格口径。'));
c.push(B('**非确定性。** 改动训练示例的一个证据字段后重跑，OURS 的一条实例（X07）输出发生变化。因此 ±1–2 个实例的差异应视为噪声。'));

c.push(H1('9  大模型使用声明与复现'));
c.push(P('本作业的代码、数据集段落、标注、术语表、校验规则和本报告由 ClawsGO Science Agent（Claude Sonnet 5.5）编写；初始 prompt 规则与每轮改写由生成器 LLM 与优化器 LLM 产生；抽取输出由被测模型产生；专家评分代理由 LLM 给出。校验方式：数据脚本断言每条证据是原文子串；校验器用注入错误测试；每个优化候选在训练集上真实执行；全部模型调用缓存在仓库的 `cache/`，`bash scripts/reproduce.sh`（默认离线）约 1 分钟复现本报告的全部数字。学生需要自行复核标注与术语表，并补充真人评分。'));
if (require.main === module) save(mkdoc(c, '实验报告'), ROOT + '/docs/实验报告.docx');
module.exports = c;
