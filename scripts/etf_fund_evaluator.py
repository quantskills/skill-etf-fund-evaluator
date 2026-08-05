#!/usr/bin/env python3
"""PandaData-only domestic equity ETF evaluator."""
from __future__ import annotations
import argparse, json, math, re, sys
from datetime import datetime
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
SCRIPT_DIR=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPT_DIR))
from metrics import capture_metrics, liquidity_metrics, premium_discount, risk_return_metrics, tracking_metrics
from pandadata_source import PandaDataSource, CallResult, fetch_etf_universe, fetch_index_bundle, fetch_product_bundle
from scoring import score_product, star_from_peer_rank

DEFAULT_JSON='/tmp/etf_evaluation.json'; DEFAULT_MD='/tmp/etf_evaluation.md'
INDEX_ALIASES={'沪深300':'000300.SH','中证300':'000300.SH','中证500':'000905.SH','中证小盘500':'000905.SH','中证1000':'000852.SH','创业板指数':'399006.SZ','创业板指':'399006.SZ','科创50':'000688.SH','上证50':'000016.SH'}

def safe(v):
 if isinstance(v,dict): return {str(k):safe(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)): return [safe(x) for x in v]
 if isinstance(v,(np.integer,)): return int(v)
 if isinstance(v,(np.floating,)): return None if not np.isfinite(v) else float(v)
 if isinstance(v,(pd.Timestamp,datetime)): return v.isoformat()
 if isinstance(v,float) and (math.isnan(v) or math.isinf(v)): return None
 return v

def norm_text(v):
 text=str(v or '').strip()
 text=re.sub(r'(收益率|全收益|净收益|指数|×|x|X|100%|95%|\s|\(|\)|（|）|\+|\*)','',text)
 return text

def resolve_benchmark(row:dict[str,Any], index_details:pd.DataFrame, override:str|None=None)->dict[str,Any]:
 if override: return {'symbol':override,'name':next((k for k,v in INDEX_ALIASES.items() if v==override),override),'method':'user_override','ambiguous':False}
 direct=str(row.get('index_symbol') or '').strip()
 if direct and direct.lower() not in ('nan','none'): return {'symbol':direct,'name':direct,'method':'metadata','ambiguous':False}
 benchmark=str(row.get('benchmark') or '')
 candidates=[]
 for name,symbol in INDEX_ALIASES.items():
  if name in benchmark: candidates.append((symbol,name))
 if not candidates and not index_details.empty and 'name' in index_details:
  for _,item in index_details.iterrows():
   name=str(item.get('name') or '')
   if name and name in benchmark: candidates.append((str(item['symbol']),name))
 unique={symbol:name for symbol,name in candidates}
 if len(unique)==1:
  symbol,name=next(iter(unique.items())); return {'symbol':symbol,'name':name,'method':'benchmark_text','ambiguous':False}
 if len(unique)>1: return {'symbol':None,'name':None,'method':'ambiguous','ambiguous':True,'candidates':unique}
 return {'symbol':None,'name':None,'method':'unresolved','ambiguous':False}

def select_universe(detail:pd.DataFrame)->pd.DataFrame:
 if detail.empty:return detail
 df=detail.copy()
 for c in ('type','etf_lof_type','index_fund_type','status','is_qdii_fund'):
  if c not in df: return pd.DataFrame()
 df=df[(df.type.astype(str)=='E')&(df.etf_lof_type.astype(str)=='ETF')&(df.index_fund_type.astype(str)=='I')]
 if 'is_qdii_fund' in df:
  df=df[df.is_qdii_fund.fillna(0).astype(str).isin(['0','0.0','False','false'])]
 if 'status' in df: df=df[df.status.astype(str).isin(['L','1','1.0'])]
 return df.drop_duplicates('symbol').reset_index(drop=True)

def dates_as_index(df):
 if df.empty or 'date' not in df:return df
 out=df.copy(); out['date']=out.date.astype(str).str.replace('-','',regex=False); out['date_dt']=pd.to_datetime(out.date,format='%Y%m%d',errors='coerce'); return out.dropna(subset=['date_dt']).sort_values('date_dt')

def returns(frame,col='close'):
 d=dates_as_index(frame)
 if d.empty or col not in d:return pd.Series(dtype=float)
 return pd.Series(pd.to_numeric(d[col],errors='coerce').pct_change().to_numpy(),index=d.date_dt).dropna()

def evaluate_product(row,source,index_details,as_of,benchmark_override=None)->dict[str,Any]:
 symbol=str(row['symbol']); resolved=resolve_benchmark(row,index_details,benchmark_override)
 result={'symbol':symbol,'name':row.get('name'),'benchmark':row.get('benchmark'),'benchmark_resolution':resolved,'metrics':{},'limitations':[]}
 if not resolved.get('symbol'):
  result['limitations'].append('无法唯一解析业绩基准；请使用 --benchmark-symbol'); return result
 bundle=fetch_product_bundle(source,symbol,as_of)
 index=fetch_index_bundle(source,resolved['symbol'],as_of)
 daily=dates_as_index(bundle['daily'].data if bundle['daily'].ok else pd.DataFrame()); raw=dates_as_index(bundle['raw'].data if bundle['raw'].ok else pd.DataFrame()); flow=bundle['flow'].data if bundle['flow'].ok else pd.DataFrame(); cr=bundle['cr'].data if bundle['cr'].ok else pd.DataFrame(); basket=bundle['basket'].data if bundle['basket'].ok else pd.DataFrame(); bench=dates_as_index(index.data if index.ok else pd.DataFrame())
 if daily.empty: result['limitations'].append('复权行情不可用')
 if bench.empty: result['limitations'].append('基准指数行情不可用')
 etf_r=returns(daily); bench_r=returns(bench)
 aligned=pd.concat([etf_r.rename('etf'),bench_r.rename('benchmark')],axis=1).dropna()
 m={}
 m.update(risk_return_metrics(daily))
 tm=tracking_metrics(aligned.etf,aligned.benchmark); m.update(tm)
 m.update({f'capture_{k}':v for k,v in capture_metrics(aligned.etf.resample('ME').apply(lambda x:(1+x).prod()-1),aligned.benchmark.resample('ME').apply(lambda x:(1+x).prod()-1)).items()})
 m.update(liquidity_metrics(raw,flow)); m.update(premium_discount(flow,raw))
 size=pd.to_numeric(flow.get('size',pd.Series(dtype=float)),errors='coerce').dropna(); m['latest_size']=float(size.iloc[-1]) if len(size) else None
 listed=str(row.get('listed_date') or row.get('found_date') or '');
 try:m['listed_years']=max(0,(datetime.strptime(as_of,'%Y%m%d')-datetime.strptime(listed.replace('-',''),'%Y%m%d')).days/365.25)
 except Exception:m['listed_years']=None
 expected=max(1,min(756,int(m.get('observations',0)))); m['data_completeness']=min(1,m.get('observations',0)/expected) if m.get('observations') else None
 if not cr.empty:
  flags=[]
  for c in ('purchase_allowed_flag','redemption_allowed_flag'):
   if c in cr: flags.append(pd.to_numeric(cr[c],errors='coerce').tail(60).mean())
  m['creation_redemption_rate']=float(np.mean(flags)) if flags else None
 else:m['creation_redemption_rate']=None
 m['basket_availability']=float(basket['stock_symbol'].notna().mean()) if not basket.empty and 'stock_symbol' in basket else None
 m['active_status']=1.0 if str(row.get('status')) in ('L','1','1.0') else 0.0
 m['tracking_difference_abs']=abs(m['tracking_difference']) if m.get('tracking_difference') is not None else None
 m['beta_distance']=abs(m['beta']-1) if m.get('beta') is not None else None
 result['metrics']=safe(m); result['sources']={k:v.provenance() for k,v in bundle.items()}; result['sources']['benchmark']=index.provenance(); result['limitations'] += [f'{k}: {v.error or v.status}' for k,v in bundle.items() if not v.ok]
 return result

def parse_args():
 p=argparse.ArgumentParser(description='PandaData境内股票指数ETF评价与同类比较')
 p.add_argument('--symbol'); p.add_argument('--symbols',nargs='*',default=[]); p.add_argument('--benchmark-name'); p.add_argument('--benchmark-symbol'); p.add_argument('--top-n',type=int,default=10); p.add_argument('--as-of'); p.add_argument('--out-json',default=DEFAULT_JSON); p.add_argument('--out-md',default=DEFAULT_MD); p.add_argument('--probe-only',action='store_true'); return p.parse_args()

def as_of(source,requested):
 if requested:return requested.replace('-','')
 return datetime.now().strftime('%Y%m%d')

def build_report(source,args):
 date=as_of(source,args.as_of); universe=fetch_etf_universe(source); detail=select_universe(universe.data if universe.ok else pd.DataFrame()); index_details=source.call('get_index_detail',fields=[]); idx=index_details.data if index_details.ok else pd.DataFrame()
 if args.probe_only:return {'mode':'probe','as_of':date,'interfaces':[x.provenance() for x in source.calls]}
 symbols=[]
 focus_symbol=None
 if args.symbol:
  focus_symbol=args.symbol.upper()
  focus_row=detail[detail['symbol'].astype(str)==focus_symbol]
  if focus_row.empty: raise RuntimeError('未找到可评价的境内股票指数ETF')
  target=resolve_benchmark(focus_row.iloc[0].to_dict(),idx,args.benchmark_symbol).get('symbol')
  if not target: raise RuntimeError('该ETF无法唯一解析业绩基准，请使用 --benchmark-symbol')
  peer_rows=[]
  for _,r in detail.iterrows():
   if resolve_benchmark(r.to_dict(),idx,args.benchmark_symbol).get('symbol')==target: peer_rows.append(r)
  peer_rows=sorted(peer_rows,key=lambda r:float(r.get('circulating_shares') or 0),reverse=True)
  symbols=[str(r['symbol']) for r in peer_rows[:max(args.top_n,10)]]
  if focus_symbol not in symbols: symbols[-1]=focus_symbol
 elif args.symbols:
  symbols=[x.upper() for x in args.symbols]
 elif args.benchmark_name:
  target=INDEX_ALIASES.get(args.benchmark_name,args.benchmark_name); rows=[]
  for _,r in detail.iterrows():
   x=resolve_benchmark(r.to_dict(),idx,args.benchmark_symbol)
   name=str(r.get('name',''))
   if x.get('symbol')==target and 'ETF' in name and not any(t in name for t in ('医药','非银行','红利','增强','质量','成长','价值')): rows.append(r)
  rows=sorted(rows,key=lambda r:float(r.get('circulating_shares') or 0),reverse=True)[:args.top_n]; symbols=[str(r['symbol']) for r in rows]
 else: raise RuntimeError('请传入 --symbol、--symbols 或 --benchmark-name')
 rows=detail[detail['symbol'].astype(str).isin(symbols)].copy()
 if rows.empty: raise RuntimeError('未找到可评价的境内股票指数ETF')
 evaluated=[evaluate_product(r.to_dict(),source,idx,date,args.benchmark_symbol) for _,r in rows.iterrows()]
 groups={}
 for item in evaluated: groups.setdefault(item['benchmark_resolution'].get('symbol'),[]).append(item)
 for group in groups.values():
  peer=[x['metrics'] for x in group];
  for item in group:
   item['rating']=score_product(item['metrics'],peer)
  item['stars']=star_from_peer_rank(item['rating']['total_score'],[x['rating']['total_score'] for x in group]) if item['rating']['total_score'] is not None else None
 return {'mode':'scan','as_of':date,'universe_count':len(detail),'products':evaluated,'provenance':source.provenance(),'methodology':{'source':'PandaData only','risk_free_rate':0,'peer_rule':'same benchmark only'}}

def markdown(r):
 lines=['# ETF基金评价报告','',f"- 分析日：`{r['as_of']}`",f"- 评价范围：境内非QDII股票指数ETF",'']
 for p in r.get('products',[]):
  rating=p.get('rating',{}); lines += [f"## {p['symbol']} {p.get('name') or ''}",'',f"- 基准：{p['benchmark_resolution'].get('name') or 'N/A'} ({p['benchmark_resolution'].get('symbol') or 'N/A'})",f"- 总分：**{rating.get('total_score') or 'N/A'}/100**；星级：**{p.get('stars') or 'N/A'}**；覆盖率：{rating.get('coverage_pct','N/A')}%",'','| 维度 | 得分 | 覆盖率 |','|---|---:|---:|']
  for k,v in rating.get('dimensions',{}).items(): lines.append(f"| {k} | {v.get('score') or 'N/A'} | {v.get('coverage_pct','N/A')}% |")
  m=p.get('metrics',{}); lines += ['',f"- 年化收益：{fmt(m.get('annual_return'))}；夏普：{fmt(m.get('sharpe'))}；最大回撤：{fmt(m.get('max_drawdown'))}",f"- 年化跟踪误差：{fmt(m.get('tracking_error'))}；R²：{fmt(m.get('r_squared'))}；折溢价绝对均值：{fmt(m.get('premium_discount_abs_mean'))}",f"- 20日成交额：{fmt(m.get('amount_mean_20'))}；最新规模：{fmt(m.get('latest_size'))}",f"- 限制：{'；'.join(p.get('limitations',[])) or '无'}",'']
 lines += ['## 口径与限制','', '- 同类排名仅在相同标的指数ETF之间进行。','- PandaData当前未提供完整费率、场外基金净值和定期报告持仓，因此本报告不评价费率或主动管理能力。','- 资金流指标代表份额/申赎变化，不等于未来收益信号。','- 申赎篮子不是基金真实持仓。','', '> 本报告仅供研究参考，不构成投资建议。']
 return '\n'.join(lines)+'\n'
def fmt(x):
 if x is None:return 'N/A'
 if abs(x)<2:return f'{x*100:.2f}%'
 return f'{x:.2f}'

def main():
 args=parse_args(); source=PandaDataSource(); report=build_report(source,args); Path(args.out_json).write_text(json.dumps(safe(report),ensure_ascii=False,indent=2)); Path(args.out_md).write_text(markdown(safe(report))); print('ETF评价完成'); print('JSON:',args.out_json); print('Markdown:',args.out_md)
if __name__=='__main__':main()
