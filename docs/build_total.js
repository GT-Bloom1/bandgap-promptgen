// 总文档:封面、摘要、相关工作、目录 + 第一至四部分 + 参考文献 + 附录。node docs/build_total.js
const L = require('./lib.js');
const D = L.D;
const { P, H1, NOTE, PART, mkdoc, save, S, ROOT, AlignmentType, Paragraph, TextRun } = L;
const pt = L.pt, g = (k) => S[k].all;
const mid = (t, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: o.before || 0, after: o.after || 120 }, children: [new TextRun({ text: t, font: o.font || 'SimSun', size: o.size || 24, bold: o.bold, color: o.color })] });
const c = [];

// ---- 封面 ----
c.push(mid('', { before: 2400 }));
c.push(mid('面向 AI4S 科研任务的 Prompt 自动生成', { font: 'SimHei', size: 44, bold: true, color: '1F3864', after: 200 }));
c.push(mid('方案设计与验证:材料文献带隙抽取', { font: 'SimHei', size: 32, bold: true, color: '2E5C8A', after: 600 }));
c.push(mid('总文档(方案文档 + 实验报告 + 演示脚本 + 声明与核对 + 参考文献 + 附录)', { size: 22, after: 900 }));
c.push(mid('硕士研究生课程作业', { size: 26, after: 160 }));
c.push(mid('姓名:______________     学号:______________', { size: 26, after: 160 }));
c.push(mid('日期:2026-11-05', { size: 24, after: 160 }));
c.push(mid('材料整理:ClawsGO Science Agent', { size: 22, color: '555555' }));

// ---- 摘要与相关工作(顶层标题,不缩进) ----
c.push(new Paragraph({ pageBreakBefore: true, children: [] }));
c.push(H1('摘要'));
c.push(P(`本作业选择“材料论文段落中的带隙抽取”作为 AI4S 子任务:输入一段英文论文文字,输出 JSON 数组,每条记录含材料、带隙数值与单位、换算后的 eV 值、方法(实验/DFT/其他计算)、带隙类型(光学/电子/未说明)和原文证据。问题分析归纳出五类理解障碍(术语歧义、单位与换算、输出格式、只收本文结果的默认前提、什么算一个带隙),每类附有人工 prompt 或直接生成 prompt 的真实失败输出。方案含五个组件:任务 schema、知识注入(术语表、示例检索、材料参考表)、生成器(模板骨架加 LLM 撰写规则)、优化闭环(候选真实执行、依据训练集失败样例改写、择优早停)、验证机制(格式与枚举、单位换算、数值范围、证据链、文献值区间、重复运行一致性)。`));
c.push(P(`实验用 101 条自写标注实例(训练 26,测试 40,困难 30,演示 5),其中 70 条测试与困难实例用于评测。实例级严格准确率:本方案 ${pt(g('OURS').acc)}%,人工 prompt A ${pt(g('A_manual').acc)}%,LLM 直接生成 prompt B ${pt(g('B_direct_llm').acc)}%;本方案相对 A、B 的差异经 bootstrap 区间与精确 McNemar 检验显著。严格 JSON 合规率:本方案 ${pt(g('OURS').fmt)}%,A ${pt(g('A_manual').fmt)}%。同样写出 schema 的人工 prompt A2 达到 ${pt(g('A2_manual_schema').acc)}%,与本方案无显著差异,说明提升的主要来源是任务形式化。消融中去掉知识注入(${pt(g('OURS_noKB').acc)}%)与去掉优化闭环(${pt(g('OURS_noLoop').acc)}%)均未测得显著下降。同一 prompt 重复运行 3 次,严格准确率在 94.3% 到 98.6% 之间。报告还给出 7 个失败案例、成本摊销分析、3 个全新段落上的补充观察和大模型使用声明。`));
c.push(NOTE('局限先行说明:数据由作者撰写而非摘自论文原文;目标模型是 Claude Sonnet 5.5(Haiku 4.5 在网关中不可用);专家评分是 LLM 评审代理,真人盲评表已备好但尚未回收;姓名学号待填。'));
c.push(H1('相关工作与定位'));
c.push(P('自动 prompt 优化方面,APE [1] 用 LLM 枚举候选指令并按执行得分择优,OPRO [2] 把历史候选与得分放进上下文让 LLM 继续提出新候选,TextGrad [3] 把文本反馈当作梯度回传,DSPy [4] 把 prompt 流程声明为可编译的模块,Self-Refine [5] 与 ReAct [6] 说明了依据反馈修正输出的做法。本方案的优化闭环取 APE 与 OPRO 的候选生成加真实执行打分,校验失败后的修复重试沿用 Self-Refine 的思路,示例检索参考 Rubin 等 [7] 的“按相似度选示例”。'));
c.push(P('在材料文献信息抽取方面,Dong 与 Cole [9] 用 ChemDataExtractor 自动构建了半导体带隙数据库,Dagdelen 等 [8] 微调 LLM 做联合实体与关系抽取,二者需要规则库或带标注的微调数据。本作业只通过 prompt 完成,不更新模型参数。科学任务评测方面,SciBench [12] 与 ChemBench [13] 主要是问答型基准,没有覆盖“从段落抽取带单位和方法的结构化记录”,所以本作业自建评测集。带隙领域知识(吸收边换算与 Tauc 外推 [10]、PBE 泛函低估带隙 [11])写入术语表与校验规则。统计上用 bootstrap [14] 给置信区间,用精确 McNemar 检验 [15] 比较配对的对错。'));

// ---- 目录 ----
c.push(new Paragraph({ pageBreakBefore: true, children: [new TextRun({ text: '目录', font: 'SimHei', size: 32, bold: true, color: '1F3864' })], spacing: { after: 160 } }));
c.push(new D.TableOfContents('目录', { hyperlink: true, headingStyleRange: '1-2' }));

// ---- 正文:先置 SHIFT 再 require,模块在加载时调用 H1/H2 ----
L.SHIFT.n = 1;
const plan = require('./build_plan.js').slice(3);
const rep = require('./build_report.js').slice(2);
const { part3, part4 } = require('./part34.js')(L);
c.push(PART('第一部分  方案文档'), ...plan);
c.push(PART('第二部分  实验报告'), ...rep);
c.push(PART('第三部分  5 分钟现场演示脚本'), ...part3);
c.push(PART('第四部分  大模型使用声明与要求核对'), ...part4);
c.push(...require('./appx.js')(L));
c.push(...require('./appx_data.js')(L));
c.push(...require('./appx_fail.js')(L));

const out = ROOT + '/docs/总文档.docx';
save(mkdoc(c, '面向 AI4S 科研任务的 Prompt 自动生成:总文档'), out);
