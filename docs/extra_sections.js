// 实验报告第 6.3–6.5 节：可复现性检验、成本摊销、三个全新段落。数字均读自 results/*.json。
const fs = require('fs');
module.exports = (L) => {
  const { P, H2, CAP, NOTE, table, B, ROOT } = L;
  const RC = JSON.parse(fs.readFileSync(ROOT + '/results/repro_check.json', 'utf8'));
  const OT = JSON.parse(fs.readFileSync(ROOT + '/results/opt_trace_std_kb.json', 'utf8'));
  const S = JSON.parse(fs.readFileSync(ROOT + '/results/summary.json', 'utf8'));
  const pc = (x) => (x * 100).toFixed(1);
  const c = [];

  c.push(H2('6.3  可复现性检验'));
  c.push(P('校验机制的第四项是可复现性。做法分两层。第一层是记录：每次模型调用的完整请求（模型名、system、user、max_tokens、温度、sample_id）取 SHA-256 作为键，请求、原始输出和 token 数一并存入 `cache/`，`bash scripts/reproduce.sh` 默认只读缓存，所以报告里的数字可以逐位复现。第二层是重复：温度固定为 0，用不同的 sample_id 绕开缓存，对同一份最终 prompt 在 70 条测试实例上再真实调用两次（`src/repro_check.py`），看输出是否稳定。'));
  const rows = Object.entries(RC.runs).map(([k, v]) => [k === '0' ? '首次（报告主结果）' : `重复 ${k}`, pc(v.acc), pc(v.fmt), k === '0' ? '-' : pc(RC.pairwise_same_content[`0_vs_${k}`]), v.failed_ids.join('、')]);
  c.push(CAP('表 6.3  同一最终 prompt 的三次运行（70 条测试实例）'));
  c.push(table(['运行', '严格准确率 %', '格式合规率 %', '与首次的科学内容一致率 %', '严格口径下判错的实例'], rows, [2300, 1500, 1500, 2100, 2238], { size: 17, alignNum: true }));
  c.push(NOTE('“科学内容一致”指两次输出的记录集合在 eV 值（取两位小数）、method、gap_type 上完全相同，不比较材料名写法。'));
  c.push(P(`严格准确率在 ${pc(Math.min(...Object.values(RC.runs).map((r) => r.acc)))}% 到 ${pc(Math.max(...Object.values(RC.runs).map((r) => r.acc)))}% 之间波动。逐例核对原因：X09、X11、X36、X38 的差异来自材料名写法，例如 “h-BN” 与 “hexagonal boron nitride films (CVD on Cu)”，严格口径按名称匹配所以判错，数值、method、gap_type 没有变；X52 是唯一一处科学内容的变化（两个值的 gap_type 首次为 unspecified，重复两次均为 optical）；X07 在三次运行中都错（失败案例 1）。去掉名称后，两次重复与首次的科学内容一致率均为 ${pc(RC.pairwise_same_content['0_vs_1'])}%（70 条中 69 条）。`));
  c.push(P('这个结果说明两点。第一，同一 prompt 在温度 0 下并不逐位稳定，API 侧的非确定性使 1 至 4 个实例的严格判定发生变化，所以第 4 节消融与第 5 节显著性检验中几个百分点以内的差异不应被解读为组件的作用。第二，方案的科学内容层面是稳定的，不稳定的主要是材料名的写法，这也是名称无关口径存在的理由。'));

  c.push(H2('6.4  成本：一次性优化与逐实例推理'));
  const opt = OT.opt_tokens, N = 70, inf = S.OURS.all.tokens;
  const am = (n) => Math.round(opt / n + inf);
  c.push(P(`标准设置下的优化闭环共调用模型 ${OT.opt_calls} 次、消耗 ${Math.round(opt / 1000)}k token（含 3 个候选在训练集上的真实执行），这是一次性成本。推理阶段本方案平均 ${Math.round(inf)} token/实例，人工 prompt A 为 ${Math.round(S.A_manual.all.tokens)}，A2 为 ${Math.round(S.A2_manual_schema.all.tokens)}。把优化成本摊到 N 个实例上，单实例成本为优化 token 除以 N 再加推理 token：N=70 时约 ${am(70)}，N=1000 时约 ${am(1000)}，N=10000 时约 ${am(10000)} token。`));
  c.push(P(`摊销后本方案仍高于 A2 的 ${Math.round(S.A2_manual_schema.all.tokens)} token，而 A2 的准确率（${pc(S.A2_manual_schema.all.acc)}%）与本方案无显著差异。所以在这个任务和这个模型上，按成本衡量最划算的是“人工写好完整 schema 约束”。本方案的价值在格式合规率 100%（A2 为 ${pc(S.A2_manual_schema.all.fmt)}%，输出常带代码围栏）和规则可由程序重新生成，需要换任务或换模型时不必重新手写。`));

  c.push(H2('6.5  三个全新段落的补充观察'));
  c.push(P('方案和全部实验定稿之后，用三个新段落再做一次未见样例检查（`data/extra_unseen/`，`python3 src/demo.py --extra` 与 `python3 src/extra_compare.py` 可复现）。这三段文字来自学生提供的另一份草稿，其备用样例是为同一任务写的，没有标注文件。判定标准在运行之前按段落内容确定：U1 应输出未掺杂与 Nb 掺杂两条（385 nm、412 nm 吸收边换算为 3.22、3.009 eV），不为只提及而未给数值的 HSE06 造记录；U2 应输出光学带隙 2.05 eV（实验）与 PBE 电子带隙 1.66 eV（DFT）两条；U3 应把 3.68、2.70、2.25 eV 按 respectively 一一对应到 ZnS、ZnSe、ZnTe。'));
  c.push(CAP('表 6.5  三个全新段落上四种方案的结果（内容正确 / 严格 JSON 合规）'));
  c.push(table(['段落', 'A 人工', 'B 直接生成', 'A2 人工+schema', '本方案'], [
    ['U1 吸收边波长 + 掺杂', '内容错：输出 []，漏掉两个 nm 吸收边 / 合规', '正确 / 合规', '正确 / 带代码围栏', '正确 / 合规'],
    ['U2 光学与电子带隙并存', '正确 / 带代码围栏', '正确 / 合规', '正确 / 带代码围栏', '正确 / 合规'],
    ['U3 respectively 并列对应', '正确 / 合规', '正确 / 合规', '正确 / 合规', '正确 / 合规'],
    ['合计', '内容 2/3，合规 2/3', '内容 3/3，合规 3/3', '内容 3/3，合规 1/3', '内容 3/3，合规 3/3'],
  ], [2300, 2200, 1700, 1900, 1538], { size: 17 }));
  c.push(P('三个样例只能当作定性补充，不能做统计推断。可以确认的有两点：人工 prompt 在 U1 上重复了主实验中的失败模式（把 nm 吸收边当作没有 eV 数值），本方案的 U1 输出把 385 nm 与 412 nm 换算到 3.22 与 3.009 eV，校验报告无错误无警告；本方案与 B 在这三段上没有差别。我原本预期 U3 的 respectively 并列会诱发数值错位，四种方案都没有出错，因此这三段没能证明本方案在并列对应上更强。'));
  return c;
};
