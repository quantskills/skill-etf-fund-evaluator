---
name: skill-etf-fund-evaluator
description: >-
  境内股票指数ETF评价与同类比较：严格使用 PandaData，评价跟踪质量、风险收益、流动性与折溢价、规模与资金流、产品稳健性五个维度，输出0–100分、同类排名和1–5星。当用户说“评价ETF”“ETF哪个好”“比较沪深300ETF”“看跟踪误差”“ETF基金测评”“找流动性好的ETF”时触发。首版不评价场外公私募基金、QDII ETF或主动管理能力。
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-etf-fund-evaluator
  repository_url: https://github.com/quantskills/skill-etf-fund-evaluator
  project_type: skill
  collection: fund-evaluation
  type: quant
  version: 1.0.1
  license: GPL-3.0-only
---

# 境内股票指数 ETF 评价

> QuantSkills 社区项目，由 GitHub 用户 `cikeqi` 维护。项目尚未经过独立审核，不代表 QuantSkills 官方认证，也不承诺收益或生产环境适用性。

## 能做什么

- 单只 ETF 深度评价：身份、业绩、跟踪误差、风险、流动性、折溢价、规模和资金流；
- 同一标的指数 ETF 横向比较和排名；
- 输出五维评分（0–100）、同类百分位、1–5 星和缺失项；
- 支持 `--as-of` 历史截止日，禁止读取之后的数据。

## 评价范围

首版只评价沪深交易所、非 QDII、被动股票指数 ETF。债券、商品、货币、跨境和主动 ETF 不与股票指数 ETF 混评。

PandaData 数据接口：`get_fund_detail`、`get_fund_daily_post`、`get_fund_daily`、`get_fund_etf_cr_net`、`get_fund_etf_cr`、`get_fund_etf_constituents`、`get_index_detail`、`get_index_daily`。

## 运行

```bash
python3.11 $SKILL/scripts/etf_fund_evaluator.py \
  --symbol 510300.SH \
  --out-json /tmp/etf_510300.json \
  --out-md /tmp/etf_510300.md
```

比较沪深300 ETF：

```bash
python3.11 $SKILL/scripts/etf_fund_evaluator.py \
  --benchmark-name 沪深300 \
  --top-n 10
```

比较指定产品：

```bash
python3.11 $SKILL/scripts/etf_fund_evaluator.py \
  --symbols 510300.SH 510330.SH 510310.SH
```

基准无法从基金资料唯一解析时显式指定：

```bash
python3.11 $SKILL/scripts/etf_fund_evaluator.py \
  --symbol 510300.SH \
  --benchmark-symbol 000300.SH
```

接口探测：

```bash
python3.11 $SKILL/scripts/etf_fund_evaluator.py --probe-only
```

## 示例问句

- “评价华泰柏瑞沪深300ETF，看看跟踪和流动性怎么样。”
- “比较跟踪沪深300的ETF，选综合评价最高的5只。”
- “找跟踪误差低、成交活跃、规模稳定的创业板ETF。”
- “510300和510500哪个更好？”
- “评价510300.SH，输出五维分数、星级和完整数据缺失说明。”

## 五维评分

| 维度 | 权重 | 核心指标 |
|---|---:|---|
| 跟踪质量 | 30% | 年化跟踪误差、跟踪偏离、R²、Beta偏离、累计偏离 |
| 风险收益 | 25% | 年化收益、波动、Sharpe、Sortino、Calmar、回撤、VaR、捕获率 |
| 流动性与交易质量 | 20% | 成交额、零成交率、折溢价均值与极值 |
| 规模与资金认可 | 15% | 规模、份额变化、净流入和持续性 |
| 产品稳健性 | 10% | 上市年限、数据完整率、申赎开放和申赎篮子 |

指标在相同标的指数的同类 ETF 中转为百分位。缺失值不填0，按可用权重归一化，并展示覆盖率。

星级沿用评价资料的同类分位规则：前10%为5星，10%–25%为4星，25%–75%为3星，75%–90%为2星，后10%为1星。有效同类样本少于5只时不强行评星。

## 重要边界

- `get_fund_etf_constituents` 是申赎清单，不是真实基金持仓；
- 资金流是份额/申赎变化，不是未来收益预测；
- 费用率、完整场外净值和定期报告持仓暂不在 PandaData 当前可用数据中，不能评价“费率最低”或主动管理能力；
- `get_fund_daily` 单次查询不超过一年，脚本会自动分段；
- 报告仅供研究参考，不构成投资建议。
