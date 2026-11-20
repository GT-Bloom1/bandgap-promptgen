// 附录 E:70 条评测实例逐条展示,按主要障碍类别分组。数据读自 data/ 与 results/。
const fs = require('fs');
module.exports = (L) => {
  const { P, H1, H2, NOTE, table, ROOT } = L;
  const rj = (f) => fs.readFileSync(`${ROOT}/${f}`, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
  const inst = [...rj('data/test.jsonl'), ...rj('data/hard.jsonl')];
  const E = JSON.parse(fs.readFileSync(ROOT + '/results/eval_rows.json', 'utf8'));
  const OUT = {}; for (const k of ['OURS']) for (const r of rj(`results/outputs/${k}.jsonl`)) OUT[r.id] = r.output;
  const ok = {}; for (const k of ['A_manual', 'B_direct_llm', 'A2_manual_schema', 'OURS']) { ok[k] = {}; for (const r of E[k]) ok[k][r.id] = r.exact; }
  const NAME = { UNIT: '单位换算', AMB: '术语歧义', METH: '方法归属', DIS: '干扰数值', CTX: '条件、相、尺寸等上下文', CONV: '标注约定', NUL: '无可抽取值' };
  const PRI = ['NUL', 'UNIT', 'AMB', 'METH', 'DIS', 'CTX', 'CONV'];
  const clean = (s) => String(s).replace(/[`*]/g, '');
  const rec = (r) => `${clean(r.material)}: ${r.unit === 'eV' ? '' : `${r.band_gap} ${r.unit} → `}${r.band_gap_eV} eV, ${r.method}, ${r.gap_type}`;
  const recs = (a) => (a.length ? a.map(rec) : ['(空数组)']);
  const parse = (s) => { try { const t = s.replace(/^```(?:json)?\s*/, '').replace(/```\s*$/, '').trim(); const v = JSON.parse(t); return Array.isArray(v) ? recs(v) : [clean(t).slice(0, 200)]; } catch (e) { return [clean(s).slice(0, 200)]; } };
  const SPLIT = {}; for (const r of E.OURS) SPLIT[r.id] = r.split === 'hard' ? '困难' : '测试';
  const mk = (v) => (v ? '✓' : '✗');
  const grp = {}; for (const r of inst) { const p = PRI.find((t) => r.tags.includes(t)); (grp[p] = grp[p] || []).push(r); }
  const c = [];
  c.push(new L.Paragraph({ pageBreakBefore: true, spacing: { after: 0, line: 20 }, children: [] }));
  c.push(H1('附录 E  70 条评测实例逐条展示'));
  c.push(P('下列 70 条是主实验的全部评测实例(测试集 40 条与困难集 30 条)。每条一个类别,类别按其标签中优先级最高的一个确定,优先级为无可抽取值、单位换算、术语歧义、方法归属、干扰数值、条件上下文、标注约定;一条实例可带多个标签,原标签列在 ID 下方。标注给出换算后的 eV 值、方法和带隙类型,本方案答对的实例,输出列只写“与标注一致”(记录、数值、方法、类型与标注相符,材料名写法可能略有不同);答错的实例给出完整输出。全部原始输出见 `results/outputs/OURS.jsonl`。对错标记依据严格口径(材料名需匹配):A 人工 prompt、B 直接生成、A2 人工加 schema,“本”表示本方案。本方案判错的实例用黄色底纹标出。'));
  c.push(NOTE('标签含义:' + Object.entries(NAME).map(([k, v]) => `${k}=${v}`).join(',') + '。训练集 26 条与演示集 5 条不在评测范围内,未列入。'));
  c.push(P('**数据划分。** 全部数据共 101 条自写段落:训练集 26 条(标注 38 条记录)、测试集 40 条(62 条)、困难集 30 条(42 条)、演示集 5 条(8 条)。没有单独的验证集:训练集同时充当优化闭环的打分集和示例库,测试集与困难集只用于最终评测,演示集只用于现场演示。划分按段落进行,不按论文,因为这些段落由作者撰写,没有来源论文,也就没有论文编号可以分组。因此评测集和训练集不是按论文隔离的:70 条评测实例中有 20 条与训练集共用至少一种材料(23 种训练材料中有 11 种也出现在评测集),但段落文字、数值和障碍设置各不相同。'));
  const cfg = ['A_manual', 'B_direct_llm', 'A2_manual_schema', 'OURS'];
  c.push(table(['类别', '实例数', 'A', 'B', 'A2', '本方案'], PRI.filter((p) => grp[p]).map((p) => [`${NAME[p]} (${p})`, grp[p].length, ...cfg.map((k) => `${grp[p].filter((r) => ok[k][r.id]).length}/${grp[p].length}`)]), [3300, 1100, 1300, 1300, 1300, 1338], { size: 17, alignNum: true }));
  for (const p of PRI) {
    if (!grp[p]) continue;
    c.push(H2(`E.${PRI.indexOf(p) + 1}  ${NAME[p]}(${grp[p].length} 条)`));
    const rows = grp[p].map((r) => [[`${r.id}(${SPLIT[r.id]})`, r.tags.join('+'), `A${mk(ok.A_manual[r.id])} B${mk(ok.B_direct_llm[r.id])}`, `A2${mk(ok.A2_manual_schema[r.id])} 本${mk(ok.OURS[r.id])}`], clean(r.text), recs(r.gold), (ok.OURS[r.id] ? ['与标注一致'] : parse(OUT[r.id] || ''))]);
    c.push(table(['编号与结果', '原文', '标注', '本方案输出'], rows, [1100, 4300, 2700, 1538], { size: 14, hl: (i) => !ok.OURS[grp[p][i].id] }));
  }
  return c;
};
