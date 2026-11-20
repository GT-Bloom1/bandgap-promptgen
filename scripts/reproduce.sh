#!/usr/bin/env bash
# 完整复现。默认 OFFLINE=1：全部大模型调用命中仓库自带的 cache/，不需要 API Key，几分钟内得到与报告一致的数字。
# 想重新调用 API(从头生成/优化/评测): OFFLINE=0 CLEAR_CACHE=1 bash scripts/reproduce.sh  (需要 ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL)
set -euo pipefail
cd "$(dirname "$0")/.."
export OFFLINE=${OFFLINE:-1}
if [ "${CLEAR_CACHE:-0}" = "1" ]; then rm -rf cache; mkdir cache; fi
python3 data/build_dataset.py                 # 1. 构造数据集并检查 evidence 是原文子串
python3 src/run_experiments.py opt            # 2. 生成初始 prompt + 优化闭环(标准/冷启动 × 有/无知识注入)
python3 src/run_experiments.py eval           # 3. 12 种配置在 70 条测试实例上的评测
python3 src/run_experiments.py judge          # 4. 专家评分代理(LLM 盲评)
python3 src/verifier_test.py                  # 5. 校验器误报率与注入错误检出率(不调用大模型)
python3 src/report.py                         # 6. 汇总表、显著性检验
python3 src/make_figures.py                   # 7. 图
python3 src/demo.py --all                     # 8. 对 5 条未见样例演示
python3 src/demo.py --extra                # 9. 3 个定稿后才写的全新段落(无标注，人工对照原文判定)
python3 src/repro_check.py 2                  # 10. 可复现性检验：同一方案重复运行 2 次，比较与首次输出的一致率
