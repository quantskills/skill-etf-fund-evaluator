# ETF 基金评价

简体中文 | [English](README.en.md)

> QuantSkills 社区项目，由 GitHub 用户 `cikeqi` 维护。项目尚未经过独立审核，不代表 QuantSkills 官方认证，也不承诺收益或生产环境适用性。

严格使用 PandaData 评价境内非QDII被动股票指数ETF，支持单只深度评价和同一标的指数横向比较。

## 配置

使用已配置的：

```text
~/.pandadata/pandadata.env
```

## 快速运行

```bash
python3.11 scripts/etf_fund_evaluator.py --symbol 510300.SH
python3.11 scripts/etf_fund_evaluator.py --benchmark-name 沪深300 --top-n 10
python3.11 scripts/etf_fund_evaluator.py --probe-only
```

默认输出：

```text
/tmp/etf_evaluation.json
/tmp/etf_evaluation.md
```

## 数据范围

| 数据 | PandaData接口 |
|---|---|
| ETF基本资料 | `get_fund_detail` |
| 复权行情 | `get_fund_daily_post` |
| 原始行情 | `get_fund_daily` |
| 份额/资金流 | `get_fund_etf_cr_net` |
| 申赎参数 | `get_fund_etf_cr` |
| 申赎清单 | `get_fund_etf_constituents` |
| 基准资料/行情 | `get_index_detail` / `get_index_daily` |

## 可以直接问的问句

### 单只ETF评价

- 评价华泰柏瑞沪深300ETF。
- 帮我评价510300.SH，并输出五维评分和同类位置。
- 分析510300的跟踪误差、流动性和资金流。
- 评价510300最近三年的风险收益表现。
- 510300的最大回撤、夏普和折溢价怎么样？
- 给510300做一份完整ETF评价报告。

### 同一指数ETF比较

- 比较跟踪沪深300的ETF，选综合评价最高的5只。
- 沪深300ETF中哪只跟踪误差最低？
- 比较沪深300ETF的规模、成交额和资金流。
- 找成交活跃、折溢价稳定、规模较大的沪深300ETF。
- 比较中证500ETF，列出综合评价前10名。
- 找创业板ETF中跟踪误差最低的5只。

### 指定多只ETF比较

- 比较510300、510310和510330。
- 510300.SH和159919.SZ哪个更好？
- 比较510300、510310、510330、159919、515330的跟踪误差和流动性。
- 对510300、510310和510330分别打分并给出同类排名。
- 比较510300和510500的风险收益表现；不同指数不要直接混排。

### 专项评价

- 哪只沪深300ETF跟踪最准确？
- 比较沪深300ETF的跟踪误差、跟踪偏离、R²和Beta。
- 找最大回撤较小、下行捕获率较低的沪深300ETF。
- 哪只沪深300ETF最近20日资金净流入最多？
- 比较沪深300ETF最近20日和60日的份额变化。
- 哪些ETF成交不足或折溢价波动较大？

### 历史截止日

- 截至2025年12月31日，评价510300。
- 只用2025年6月30日以前的数据比较沪深300ETF。
- 截至2025-01-15，找综合评价最高的中证500ETF。

### 当前不支持

- 场外公募和私募基金评价；
- QDII、债券、商品、货币ETF混合排名；
- 管理费/托管费最低产品筛选；
- 基金定期报告真实持仓和主动选股能力评价。

## 测试

```bash
python3.11 -m unittest discover -s tests -v
```

## 数据来源、假设与限制

- 数据来源：仅使用 PandaData；具体接口、字段和数据边界见 `references/`。
- 关键假设：同一标的指数的境内非 QDII 被动股票 ETF 可以进行横向比较；缺失指标按可用权重归一化。
- 已知限制：申赎清单不等于真实基金持仓；资金流不代表未来收益；费用率、完整场外净值及定期报告持仓不在当前评价范围。
- 风险边界：输出仅供研究与教育，不构成投资建议、收益承诺、产品推荐或自动交易指令。

## 维护与许可

- 维护者：GitHub 用户 `cikeqi`
- 仓库：`quantskills/skill-etf-fund-evaluator`
- 许可：[GNU GPL v3.0 only](LICENSE)（SPDX：`GPL-3.0-only`）
