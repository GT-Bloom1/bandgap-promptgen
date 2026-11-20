const fs = require('fs');
const D = require('docx');
const { Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, AlignmentType, HeadingLevel, ImageRun, LevelFormat, Footer, PageNumber, Document, Packer } = D;
const ROOT = '/home/user/ClawsGO/project-20261105-1/bandgap-promptgen';
const S = JSON.parse(fs.readFileSync(ROOT + '/results/summary.json', 'utf8'));
const VT = JSON.parse(fs.readFileSync(ROOT + '/results/verifier_test.json', 'utf8'));
const BODY = 'SimSun', HEAD = 'SimHei';
const W = 9638; // A4 内容宽度(DXA), 页边距 2cm

const f3 = (x) => x.toFixed(3);
const pt = (x) => (x * 100).toFixed(1);
const runs = (t, o = {}) => {
  // 支持 **加粗** 与 `代码` 简单标记
  const out = []; const re = /(\*\*[^*]+\*\*|`[^`]+`)/g; let last = 0, m;
  while ((m = re.exec(t))) {
    if (m.index > last) out.push(new TextRun({ text: t.slice(last, m.index), font: BODY, size: o.size || 21, ...o.run }));
    const tok = m[0];
    if (tok.startsWith('**')) out.push(new TextRun({ text: tok.slice(2, -2), bold: true, font: BODY, size: o.size || 21, ...o.run }));
    else out.push(new TextRun({ text: tok.slice(1, -1), font: 'Consolas', size: (o.size || 21) - 2, ...o.run }));
    last = m.index + tok.length;
  }
  if (last < t.length) out.push(new TextRun({ text: t.slice(last), font: BODY, size: o.size || 21, ...o.run }));
  return out;
};
const P = (t, o = {}) => new Paragraph({ children: runs(t, o), spacing: { after: o.after ?? 100, line: o.line ?? 272 }, alignment: o.align, indent: o.indent, keepNext: o.keepNext });
const SHIFT = { n: 0 };
const H1 = (t) => new Paragraph({ heading: SHIFT.n ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_1, outlineLevel: SHIFT.n ? 1 : 0, spacing: { before: 220, after: 100 }, keepNext: true, children: [new TextRun({ text: t, font: HEAD, size: 28, bold: true, color: '1F3864' })] });
const H2 = (t) => new Paragraph({ heading: SHIFT.n ? HeadingLevel.HEADING_3 : HeadingLevel.HEADING_2, outlineLevel: SHIFT.n ? 2 : 1, spacing: { before: 140, after: 80 }, keepNext: true, children: [new TextRun({ text: t, font: HEAD, size: 23, bold: true, color: '2E5C8A' })] });
const B = (t, lvl = 0) => new Paragraph({ numbering: { reference: 'bul', level: lvl }, children: runs(t), spacing: { after: 40, line: 268 } });
const N = (t) => new Paragraph({ numbering: { reference: 'num', level: 0 }, children: runs(t), spacing: { after: 40, line: 268 } });
const CAP = (t) => new Paragraph({ children: [new TextRun({ text: t, font: HEAD, size: 19, bold: true })], alignment: AlignmentType.CENTER, spacing: { before: 100, after: 60 }, keepNext: true });
const NOTE = (t) => P(t, { size: 18, run: { color: '555555' }, after: 120 });

const bd = { style: BorderStyle.SINGLE, size: 4, color: 'AAAAAA' };
const borders = { top: bd, bottom: bd, left: bd, right: bd };
function cell(content, w, o = {}) {
  const arr = (Array.isArray(content) ? content : [content]).flatMap((t) => String(t).split('\n'));
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: 'auto' } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: arr.map((t) => new Paragraph({ children: runs(String(t), { size: o.size || 18, run: o.head ? { bold: true, font: HEAD } : {} }), spacing: { after: 30, line: 250 }, alignment: o.align }))
  });
}
function table(headers, rows, widths, o = {}) {
  const sum = widths.reduce((a, b) => a + b, 0);
  const hdr = new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], { head: true, fill: 'D9E2F3', size: o.size, align: AlignmentType.CENTER })) });
  const body = rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], { size: o.size, fill: o.hl && o.hl(ri, r) ? 'FFF2CC' : undefined, align: o.alignNum && i > 0 ? AlignmentType.CENTER : undefined })) }));
  return new Table({ width: { size: sum, type: WidthType.DXA }, columnWidths: widths, rows: [hdr, ...body] });
}
function img(path, wDxa) {
  const b = fs.readFileSync(path); const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  const wPx = Math.round((wDxa / 1440) * 96), hPx = Math.round(wPx * h / w);
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new ImageRun({ type: 'png', data: b, transformation: { width: wPx, height: hPx }, altText: { title: path, description: path, name: path } })] });
}
const SP = () => new Paragraph({ children: [], spacing: { after: 60 } });
function mkdoc(children, title) {
  return new Document({
    creator: 'ClawsGO Science Agent', title,
    styles: { default: { document: { run: { font: BODY, size: 21 } } } },
    numbering: { config: [
      { reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 520, hanging: 260 } } } }, { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 900, hanging: 260 } } } }] },
      { reference: 'num', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 520, hanging: 300 } } } }] }] },
    sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: title + '   第 ', font: BODY, size: 16, color: '777777' }), new TextRun({ children: [PageNumber.CURRENT], font: BODY, size: 16, color: '777777' }), new TextRun({ text: ' 页', font: BODY, size: 16, color: '777777' })] })] }) },
      children }] });
}
async function save(doc, path) { fs.writeFileSync(path, await Packer.toBuffer(doc)); console.log('wrote', path); }
const PART = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, outlineLevel: 0, pageBreakBefore: true, spacing: { before: 0, after: 160 }, children: [new TextRun({ text: t, font: HEAD, size: 32, bold: true, color: '1F3864' })] });
const CODE = (text, size = 13) => text.replace(/\t/g, '    ').split('\n').map((ln) => new Paragraph({ spacing: { after: 0, line: 190 }, shading: { type: ShadingType.CLEAR, fill: 'F2F2F2', color: 'auto' }, children: [new TextRun({ text: ln === '' ? ' ' : ln, font: { ascii: 'Courier New', hAnsi: 'Courier New', eastAsia: 'SimSun' }, size })] }));
module.exports = { SHIFT, PART, CODE, D, P, H1, H2, B, N, CAP, NOTE, table, img, SP, mkdoc, save, S, VT, f3, pt, W, ROOT, runs, AlignmentType, Paragraph, TextRun };
