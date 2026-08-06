# ETF Fund Evaluator

[简体中文](README.md) | English

> This is a QuantSkills community project maintained by GitHub user `cikeqi`. It has not been independently audited, does not represent official QuantSkills certification, and makes no return or production-readiness guarantees.

This skill evaluates mainland China, non-QDII, passive equity-index ETFs using PandaData only. It supports in-depth evaluation of a single ETF and peer comparison among ETFs tracking the same benchmark.

## Configuration

Use the locally configured PandaData credential file:

```text
~/.pandadata/pandadata.env
```

Never commit real credentials or tokens to this repository.

## Quick Start

```bash
python3.11 scripts/etf_fund_evaluator.py --symbol 510300.SH
python3.11 scripts/etf_fund_evaluator.py --benchmark-name 沪深300 --top-n 10
python3.11 scripts/etf_fund_evaluator.py --probe-only
```

Default outputs:

```text
/tmp/etf_evaluation.json
/tmp/etf_evaluation.md
```

## Data Coverage

| Data | PandaData interface |
|---|---|
| ETF profile | `get_fund_detail` |
| Adjusted prices | `get_fund_daily_post` |
| Raw prices | `get_fund_daily` |
| Shares and fund flows | `get_fund_etf_cr_net` |
| Creation/redemption parameters | `get_fund_etf_cr` |
| Creation/redemption basket | `get_fund_etf_constituents` |
| Benchmark profile and prices | `get_index_detail` / `get_index_daily` |

## Example Questions

### Single-ETF evaluation

- Evaluate the ChinaAMC CSI 300 ETF.
- Evaluate `510300.SH` and report its five dimension scores and peer position.
- Analyze the tracking error, liquidity, and fund flows of `510300.SH`.
- Evaluate the risk-adjusted performance of `510300.SH` over the past three years.
- Report the maximum drawdown, Sharpe ratio, and premium/discount behavior of `510300.SH`.

### Compare ETFs tracking the same index

- Compare ETFs tracking the CSI 300 and list the five highest-rated products.
- Which CSI 300 ETF has the lowest tracking error?
- Compare the size, turnover, and fund flows of CSI 300 ETFs.
- Find CSI 300 ETFs with active trading, stable premiums or discounts, and substantial scale.
- Rank the top ten CSI 500 ETFs by the overall evaluation score.

### Compare specified ETFs

- Compare `510300`, `510310`, and `510330`.
- Which is stronger on tracking and liquidity: `510300.SH` or `159919.SZ`?
- Score `510300`, `510310`, and `510330` and report their peer rankings.
- Compare the risk-adjusted performance of `510300` and `510500`; do not rank products tracking different benchmarks as direct peers.

### Specialized analysis

- Which CSI 300 ETF tracks its benchmark most accurately?
- Compare tracking error, tracking difference, R-squared, and beta across CSI 300 ETFs.
- Find CSI 300 ETFs with smaller drawdowns and lower downside capture.
- Which CSI 300 ETF had the largest net inflow over the last 20 trading days?
- Compare 20-day and 60-day share changes across CSI 300 ETFs.
- Identify ETFs with insufficient trading activity or unstable premiums and discounts.

### Point-in-time evaluation

- Evaluate `510300` as of December 31, 2025.
- Compare CSI 300 ETFs using only data available by June 30, 2025.
- As of January 15, 2025, identify the highest-rated CSI 500 ETFs.

## Current Scope Exclusions

- Off-exchange public funds and private funds.
- Mixed rankings of QDII, bond, commodity, money-market, and equity ETFs.
- Screening for the lowest management or custody fees.
- Evaluation of actual periodic-report holdings or active stock-selection ability.

## Evaluation Framework

| Dimension | Weight | Core measures |
|---|---:|---|
| Tracking quality | 30% | Annualized tracking error, tracking difference, R-squared, beta deviation, cumulative deviation |
| Risk and return | 25% | Annualized return, volatility, Sharpe, Sortino, Calmar, drawdown, VaR, capture ratios |
| Liquidity and trading quality | 20% | Turnover, zero-volume ratio, average and extreme premium/discount |
| Scale and fund-flow recognition | 15% | Scale, share changes, net inflows, persistence |
| Product robustness | 10% | Listing history, data completeness, creation/redemption status and basket availability |

Indicators are converted to percentiles among ETFs tracking the same benchmark. Missing values are not replaced with zero; scores are normalized across available weights and include a coverage ratio.

Star ratings follow peer percentiles: the top 10% receive five stars, 10%–25% four stars, 25%–75% three stars, 75%–90% two stars, and the bottom 10% one star. No forced star rating is produced when fewer than five valid peers are available.

## Tests

```bash
python3.11 -m unittest discover -s tests -v
```

## Data Sources, Assumptions, and Limitations

- Data source: PandaData only; see `references/` for interfaces, fields, and source boundaries.
- Key assumption: mainland China, non-QDII, passive equity-index ETFs tracking the same benchmark can be compared as peers; missing indicators are normalized across available weights.
- Known limitations: creation/redemption baskets are not actual portfolio holdings; fund flows do not predict future returns; fees, complete off-exchange NAV data, and periodic-report holdings are outside the current scope.
- Risk boundary: outputs are for research and educational use only and are not investment advice, return guarantees, product recommendations, or automated trading instructions.

## Maintenance and License

- Maintainer: GitHub user `cikeqi`
- Repository: `quantskills/skill-etf-fund-evaluator`
- License: [GNU GPL v3.0 only](LICENSE) (`GPL-3.0-only`)
