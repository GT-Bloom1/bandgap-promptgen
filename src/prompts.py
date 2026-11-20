"""生成器（组件3）：组件化拼装 角色 / 任务定义 / 规则 / 知识 / 示例 / 自检 / 输出格式。"""
import json, os

import yaml

from llm import OPTIMIZER_MODEL, call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = yaml.safe_load(open(os.path.join(ROOT, "task", "schema.yaml"), encoding="utf-8"))

OUTPUT_FORMAT = """Output format: return ONLY a JSON array (no markdown fence, no commentary). Each element has exactly these keys:
material (string), band_gap (number as written in the text), unit (one of eV, meV, nm, um, cm-1, as written in the text),
band_gap_eV (number converted to eV, 3 decimals), method (experimental | DFT | other_calc),
gap_type (optical | electronic | unspecified), evidence (verbatim substring of the paragraph containing the number).
If the paragraph contains no extractable band gap, return []."""


def schema_block(with_constraints=True):
    """把 task/schema.yaml 渲染成给模型看的任务定义。with_constraints=False 用于冷启动实验：
    只给字段定义，抽取约束要靠优化闭环从错误中自动发现。"""
    o = SCHEMA["output"]["item"]
    lines = ["Task: extract band gap values from a materials-science paragraph.", "Field definitions:"]
    for k, v in o.items():
        lines.append(f"- {k}: {v['description']}")
    if with_constraints:
        lines.append("Extraction constraints:")
        lines += [f"- {c}" for c in SCHEMA["constraints"]]
    return "\n".join(lines)


def render_system(spec):
    parts = [spec["role"], schema_block(spec.get("with_constraints", True))]
    if spec.get("rules"):
        parts.append("Additional rules (learned from error analysis):\n" + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(spec["rules"])))
    if spec.get("self_check"):
        parts.append("Before answering, silently check:\n" + "\n".join(f"- {c}" for c in spec["self_check"]))
    parts.append(OUTPUT_FORMAT)
    return "\n\n".join(parts)


def render_user(text, glossary_items=None, examples=None):
    parts = []
    if glossary_items:
        parts.append("Relevant domain notes:\n" + "\n".join(f"- [{e['term']}] {e['text']}" for e in glossary_items))
    if examples:
        ex = []
        for i, e in enumerate(examples, 1):
            ex.append(f"Example {i}\nParagraph: {e['text']}\nAnswer: {json.dumps(e['gold'], ensure_ascii=False)}")
        parts.append("Solved examples of similar paragraphs:\n\n" + "\n\n".join(ex))
    parts.append("Paragraph:\n" + text + "\n\nAnswer:")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- 生成步骤: schema -> 初始 spec
GEN_SYSTEM = "You are an expert prompt engineer for scientific information extraction. Reply with a single JSON object only."
GEN_USER = """Below is a formal task schema (YAML) and a list of domain-knowledge topics for extracting band gap values from materials-science paragraphs.

SCHEMA:
{schema}

KNOWLEDGE TOPICS: {topics}

Write the variable components of an extraction prompt as JSON with keys:
- "role": 1-2 sentences describing the expert persona and the stakes (scientific correctness over recall).
- "rules": 6-9 short, general, actionable decision rules that help a model apply the schema constraints correctly (e.g. how to decide method, gap_type, what to skip, how to convert units). Do not mention any specific material or number.
- "self_check": 4-6 short checks the model should run on its draft before answering (unit conversion, evidence substring, skipped distractors, cited values, etc.).
Return JSON only."""


def generate_initial_spec(topics, sample_id=0, with_constraints=True):
    schema_txt = open(os.path.join(ROOT, "task", "schema.yaml"), encoding="utf-8").read()
    if not with_constraints:   # 冷启动：生成器也看不到 constraints / verification 段
        schema_txt = schema_txt.split("constraints:")[0]
    r = call(OPTIMIZER_MODEL, GEN_SYSTEM, GEN_USER.format(schema=schema_txt, topics="; ".join(topics)),
             max_tokens=2000, temperature=0.0, sample_id=sample_id)
    t = r["text"].strip()
    t = t[t.find("{"): t.rfind("}") + 1]
    spec = json.loads(t)
    return dict(role=spec["role"], rules=list(spec["rules"]), self_check=list(spec["self_check"]),
                with_constraints=with_constraints)


# ---------------------------------------------------------------- 基线 prompt
MANUAL_A = """You are an expert in materials science. Read the paragraph and extract every band gap value that is explicitly stated.
Return only a JSON array. Each element must have: material, band_gap (number as written), unit (as written), band_gap_eV (converted to eV),
method ("experimental", "DFT" or "other_calc"), gap_type ("optical", "electronic" or "unspecified"), evidence (the quoted fragment of the text).
Only extract values that are explicitly given; if there is none, return []."""

MANUAL_A2 = None  # 在 baselines 构造：A 加上完整 schema 约束（人工做了任务形式化，但没有自动生成/优化/知识注入）


def manual_a2_system():
    return MANUAL_A + "\n\n" + schema_block().split("Field definitions:")[0].replace(
        "Task: extract band gap values from a materials-science paragraph.\n", "") + "\n" + \
        "Field definitions:" + schema_block().split("Field definitions:")[1]


DIRECT_META_SYSTEM = "You are a helpful assistant that writes prompts for other LLMs."
DIRECT_META_USER = """Write a system prompt for an LLM that extracts band gap values from a paragraph of a materials-science paper.
The LLM's answer must be a JSON array; each element has the fields: material, band_gap, unit, band_gap_eV, method (experimental | DFT | other_calc), gap_type (optical | electronic | unspecified), evidence.
Return only the prompt text."""


def direct_llm_prompt():
    r = call(OPTIMIZER_MODEL, DIRECT_META_SYSTEM, DIRECT_META_USER, max_tokens=1500, temperature=0.0)
    return r["text"].strip()
