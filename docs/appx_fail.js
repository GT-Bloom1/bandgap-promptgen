// 附录 F:失败案例的提示词(系统提示词 + 实际发送的用户消息)、金标准与模型原始输出。
// 提示词由 src/dump_failure_prompts.py 重建,并已验证与缓存中的真实请求一致。
const fs = require('fs');
module.exports = (L) => {
  const { P, H1, H2, NOTE, CODE, table, ROOT } = L;
  const rj = (f) => fs.readFileSync(`${ROOT}/${f}`, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
  const FP = JSON.parse(fs.readFileSync(ROOT + '/results/failure_prompts.json', 'utf8'));
  const DATA = {}; for (const f of ['test', 'hard']) for (const r of rj(`data/${f}.jsonl`)) DATA[r.id] = r;
  const out = (cfg) => { const m = {}; for (const r of rj(`results/outputs/${cfg}.jsonl`)) m[r.id] = r.output; return m; };
  const w = (ch) => (/[⺀-鿿＀-￯　-〿]/.test(ch) ? 2 : 1);
  const wrap = (s, n = 118) => s.split('\n').flatMap((ln) => { const res = []; let cur = '', cw = 0; for (const ch of ln) { if (cw + w(ch) > n) { res.push(cur); cur = ''; cw = 0; } cur += ch; cw += w(ch); } res.push(cur); return res; });
  const show = (s) => {
    const fence = /^\s*```/.test(s);
    const t = s.replace(/^\s*```(?:json)?\s*/, '').replace(/```\s*$/, '').trim();
    try { const v = JSON.parse(t); return (fence ? ['# 原输出带 ```json 代码围栏'] : []).concat('[', v.map((x, i) => '  ' + JSON.stringify(x) + (i < v.length - 1 ? ',' : '')), ']'); } catch (e) { return t.split('\n'); }
  };
  const why = { 'X07': '并列分句里后半句没有继承测试技术,纳米片被标成 unspecified(金标准 optical)。', 'X52': '原文没有逐一写明技术,金标准是按“同条件测得”推断的,标注可争议。', 'X11': '数值、方法、类型全对,只是材料名写法与金标准不同,严格口径判错。', 'X38': '同案例 3a:材料名写成 hydrogen-terminated silicon quantum dots。', 'X66': '没有术语表,没认出 Tran-Blaha modified Becke-Johnson 是 DFT 方法,漏掉 3.2 eV。', 'X19': '闭环写出的规则过窄,只写吸收边位置的段落漏掉了 255 nm。', 'X18': '把对照用的体相硅 1.12 eV 当成本文结果。', 'X41': 'schema 里没有“范围”规则,把范围两端各输出一条。' };
  const CN = { OURS: '本方案', OURS_noKB: '本方案去掉知识注入', COLD_loop: '冷启动,只有闭环', COLD_KB: '冷启动,只有知识注入', A2_manual_schema: '人工加 schema(A2)' };
  const c = [H1('附录 F  失败案例的提示词、原始输入与输出')];
  c.push(P('第二部分第 7 节的失败案例并不使用同一份提示词:它们来自五种配置,系统提示词各不相同(表 F.1)。带知识注入的配置,每个实例的用户消息还不同,里面是按该段落从术语表和训练集检索出的术语与示例。本附录给出每个案例当时实际发送的系统提示词、用户消息、金标准和模型的原始输出。提示词由 `src/dump_failure_prompts.py` 重建,并逐个验证与缓存中的真实请求一致(`results/failure_prompts.json` 中 `matches_cached_request` 全为 true);输出取自 `results/outputs/`,未作修改。'));
  c.push(table(['案例', '实例', '配置', '系统提示词', '检索术语与示例'], FP.map((r) => [r.case, r.id, CN[r.config], r.system_name === 'std_kb_optimized_spec' ? `${r.system_name}(附录 B)` : `${r.system_name}(F.0)`, r.config === 'A2_manual_schema' ? '无' : /nokb|COLD_loop/.test(r.system_name + r.config) ? '否' : '是']), [900, 800, 2600, 3600, 1738], { size: 17 }));
  c.push(NOTE('表 F.1  失败案例对应的配置与提示词。系统提示词在同一配置内对所有实例相同。'));
  c.push(H2('F.0  其余配置的系统提示词'));
  const seen = new Set();
  for (const r of FP) {
    if (r.system_name === 'std_kb_optimized_spec' || seen.has(r.system_name)) continue;
    seen.add(r.system_name);
    c.push(P(`**${r.system_name}**(${r.system.length} 字符)`, { after: 40, keepNext: true }));
    c.push(...CODE(wrap(r.system).join('\n'), 13));
    c.push(P('', { after: 60 }));
  }
  for (const r of FP) {
    const d = DATA[r.id];
    c.push(H2(`${r.case}  ${CN[r.config]},实例 ${r.id}`));
    c.push(NOTE('原因:' + why[r.id]));
    const sys = r.system_name === 'std_kb_optimized_spec' ? '# 系统提示词: std_kb_optimized_spec,全文见附录 B' : `# 系统提示词: ${r.system_name},全文见 F.0`;
    const lines = [sys, '', '# 用户消息(实际发送,末尾为待抽取段落)', ...wrap(r.user), '', '# 金标准', '[', ...d.gold.map((x, i) => '  ' + JSON.stringify(x) + (i < d.gold.length - 1 ? ',' : '')), ']', '', `# 模型原始输出(${CN[r.config]})`, ...show(out(r.config)[r.id])];
    c.push(...CODE(lines.flatMap((l) => wrap(l)).join('\n'), 13));
  }
  return c;
};
