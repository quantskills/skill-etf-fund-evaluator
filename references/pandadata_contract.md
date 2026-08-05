# PandaData ETF数据契约

## 已实测接口

| 模块 | 方法 | 实测说明 |
|---|---|---|
| 基本资料 | `get_fund_detail` | 可返回ETF名称、类型、基准文本、上市日、规模等；`index_symbol`部分产品为空 |
| 原始行情 | `get_fund_daily` | 可用；单次日期范围不得超过1年 |
| 前复权行情 | `get_fund_daily_pre` | 可用；单次日期范围不得超过1年 |
| 后复权行情 | `get_fund_daily_post` | 可用；单次日期范围不得超过1年 |
| 净申赎 | `get_fund_etf_cr_net` | 可返回shares、shares_change、size、size_change、net_inflow、unit_nav、close等 |
| 申赎清单参数 | `get_fund_etf_cr` | 可返回unit_nav、creation_unit、申赎限制与现金替代字段 |
| 申赎清单成分 | `get_fund_etf_constituents` | 可返回stock_symbol、quantity和现金替代字段；不是实际持仓 |
| 指数资料 | `get_index_detail` | 可用于基准名称和代码映射 |
| 指数行情 | `get_index_daily` | 可用于跟踪质量比较 |

## 认证

只读取环境变量 `PANDA_USERNAME`、`PANDA_PASSWORD` 或 `~/.pandadata/pandadata.env`，不把凭证写入报告。

## 时间边界

`--as-of` 是硬截止日。行情接口自动按最多364个自然日分段，所有合并数据再次截断到分析日。

## 已知限制

- 基金单次日线接口日期跨度不能超过一年；
- 基准代码可能不在基金详情中，需要根据benchmark文本与指数资料映射；
- 基准文本可能对应多个指数，歧义时必须要求显式基准；
- 当前首版不使用费率、场外净值、基金定期报告持仓；
- ETF资金流是份额/申赎变化，不是预测信号。
