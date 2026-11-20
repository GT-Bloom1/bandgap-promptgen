// 参考文献与附录。附录内容在构建时直接读取仓库文件,保证与代码一致。
const fs = require('fs');
const cp = require('child_process');
module.exports = (L) => {
  const { P, H1, NOTE, CODE, PART, table, ROOT } = L;
  const rd = (f) => fs.readFileSync(ROOT + '/' + f, 'utf8').replace(/\s+$/, '');
  const c = [];

  c.push(PART('参考文献'));
  const refs = [
    'Zhou Y., Muresanu A. I., Han Z., et al. Large language models are human-level prompt engineers (APE). ICLR 2023. arXiv:2211.01910.',
    'Yang C., Wang X., Lu Y., et al. Large language models as optimizers (OPRO). ICLR 2024. arXiv:2309.03409.',
    'Yuksekgonul M., Bianchi F., Boen J., et al. Optimizing generative AI by backpropagating language model feedback. Nature 639, 609–616 (2025). 预印本题名:TextGrad: Automatic “Differentiation” via Text, arXiv:2406.07496.',
    'Khattab O., Singhvi A., Maheshwari P., et al. DSPy: Compiling declarative language model calls into self-improving pipelines. ICLR 2024. arXiv:2310.03714.',
    'Madaan A., Tandon N., Gupta P., et al. Self-Refine: Iterative refinement with self-feedback. NeurIPS 2023. arXiv:2303.17651.',
    'Yao S., Zhao J., Yu D., et al. ReAct: Synergizing reasoning and acting in language models. ICLR 2023. arXiv:2210.03629.',
    'Rubin O., Herzig J., Berant J. Learning to retrieve prompts for in-context learning. NAACL 2022, 2655–2671. arXiv:2112.08633.',
    'Dagdelen J., Dunn A., Lee S., et al. Structured information extraction from scientific text with large language models. Nature Communications 15, 1418 (2024).',
    'Dong Q., Cole J. M. Auto-generated database of semiconductor band gaps using ChemDataExtractor. Scientific Data 9, 193 (2022).',
    'Tauc J., Grigorovici R., Vancu A. Optical properties and electronic structure of amorphous germanium. Physica Status Solidi (b) 15, 627–637 (1966).',
    'Perdew J. P., Burke K., Ernzerhof M. Generalized gradient approximation made simple. Physical Review Letters 77, 3865–3868 (1996).',
    'Wang X., Hu Z., Lu P., et al. SciBench: Evaluating college-level scientific problem-solving abilities of large language models. ICML 2024. arXiv:2307.10635.',
    'Mirza A., Alampara N., Kunchapu S., et al. Are large language models superhuman chemists? (ChemBench). arXiv:2404.01475.',
    'Efron B. Bootstrap methods: another look at the jackknife. The Annals of Statistics 7(1), 1–26 (1979).',
    'McNemar Q. Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika 12, 153–157 (1947).',
  ];
  const urls = ['arxiv.org/abs/2211.01910', 'arxiv.org/abs/2309.03409', 'doi.org/10.1038/s41586-025-08661-4', 'arxiv.org/abs/2310.03714', 'arxiv.org/abs/2303.17651', 'arxiv.org/abs/2210.03629', 'arxiv.org/abs/2112.08633', 'doi.org/10.1038/s41467-024-45563-x', 'doi.org/10.1038/s41597-022-01294-6', 'doi.org/10.1002/pssb.19660150224', 'doi.org/10.1103/PhysRevLett.77.3865', 'arxiv.org/abs/2307.10635', 'arxiv.org/abs/2404.01475', 'doi.org/10.1214/aos/1176344552', 'doi.org/10.1007/BF02295996'];
  const f = { font: 'SimSun', size: 19 };
  refs.forEach((t, i) => c.push(new L.Paragraph({ spacing: { after: 60, line: 280 }, indent: { left: 520, hanging: 520 }, children: [new L.TextRun({ text: `[${i + 1}]  ${t} `, ...f }), new L.D.ExternalHyperlink({ link: 'https://' + urls[i], children: [new L.TextRun({ text: 'https://' + urls[i], ...f, color: '0563C1', underline: {} })] })] })));
  c.push(NOTE('说明:全部 15 条的链接已核对。九条 arXiv 页面的题名与作者和上文一致,[2][6][7][12] 的会议名在页面备注中可见,[1][4][5] 的会议名(ICLR 2023、ICLR 2024、NeurIPS 2023)页面未标出,凭已有知识写出,请自行核对;七个 DOI 经 Crossref 核对,题名、作者、期刊、卷页一致。[3] 引用的是 Nature 正式版,arXiv 预印本的题名不同。[6] ReAct 在正文中用于说明“观察校验反馈后再行动”的思路。'));

  c.push(PART('附录'));
  c.push(H1('附录 A  任务 schema(task/schema.yaml 全文)'));
  c.push(...CODE(rd('task/schema.yaml'), 15));
  c.push(H1('附录 B  最终优化后的 system prompt'));
  const tmp = '/tmp/final_prompt.txt';
  cp.execSync(`cd ${ROOT} && python3 -c "import sys,json;sys.path.insert(0,'src');import prompts;print(prompts.render_system(json.load(open('prompts/std_kb_optimized_spec.json',encoding='utf-8'))))" > ${tmp}`);
  c.push(NOTE('由 `render_system(std_kb_optimized_spec)` 生成,不含检索得到的术语和示例(这部分每个实例不同)。'));
  c.push(...CODE(fs.readFileSync(tmp, 'utf8').replace(/\s+$/, ''), 14));
  c.push(H1('附录 C  复现命令(scripts/reproduce.sh)'));
  c.push(NOTE('默认只读缓存(OFFLINE=1),可在没有网络和 API key 的机器上复现报告中的全部数字;设 `OFFLINE=0` 并提供 `ANTHROPIC_API_KEY` 则重新调用模型。'));
  c.push(...CODE(rd('scripts/reproduce.sh'), 15));
  c.push(H1('附录 D  关键代码'));
  for (const f of ['src/verifier.py', 'src/optimizer.py']) {
    c.push(P(`**${f}**`, { after: 40, keepNext: true }));
    c.push(...CODE(rd(f), 12));
    c.push(P('', { after: 60 }));
  }
  c.push(NOTE('这里只列校验器和优化器两个核心文件;检索(src/retrieval.py)、执行与修复重试(src/pipeline.py)、重复运行检验(src/repro_check.py)、评分(src/scoring.py)、LLM 封装与缓存(src/llm.py)、实验驱动(src/run_experiments.py)等其余代码见代码仓库。'));
  return c;
};
