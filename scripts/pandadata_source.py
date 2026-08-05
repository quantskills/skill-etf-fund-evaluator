"""PandaData ETF source layer with bounded windows and provenance."""
from __future__ import annotations
import os, re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
import pandas as pd

ENV_FILE = Path.home()/'.pandadata'/'pandadata.env'
SENSITIVE = re.compile(r'(?i)(password|passwd|token|username)\s*[=:]\s*[^\s,;]+')

@dataclass
class CallResult:
    method: str
    status: str
    data: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    rows: int = 0
    columns: list[str] = field(default_factory=list)
    latest_date: str|None = None
    params: dict[str,Any] = field(default_factory=dict)
    error: str|None = None
    attempts: int = 1
    @property
    def ok(self): return self.status == 'ok'
    def provenance(self):
        return {'method':self.method,'status':self.status,'rows':self.rows,'columns':self.columns,'latest_date':self.latest_date,'params':self.params,'error':self.error,'attempts':self.attempts}

def load_env():
    vals={}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
            line=line.strip()
            if line and not line.startswith('#') and '=' in line:
                k,v=line.split('=',1); vals[k.strip()]=v.strip().strip('"\'')
    return vals

def init_api():
    try: import panda_data
    except ImportError as exc: raise RuntimeError('未安装 panda_data') from exc
    env=load_env(); user=os.getenv('PANDA_USERNAME') or env.get('PANDA_USERNAME',''); password=os.getenv('PANDA_PASSWORD') or env.get('PANDA_PASSWORD','')
    if not user or not password: raise RuntimeError('缺少 PandaData 凭证，请配置环境变量或 ~/.pandadata/pandadata.env')
    panda_data.init_token(username=user,password=password)
    return panda_data

def safe_error(e): return SENSITIVE.sub(lambda m:f'{m.group(1)}=<redacted>',str(e))[:500]
def date_window(end, days): return ((datetime.strptime(end,'%Y%m%d')-timedelta(days=days)).strftime('%Y%m%d'),end)
def latest_date(df):
    for c in ('date','listed_date','found_date'):
        if c in df and df[c].notna().any(): return str(df[c].dropna().astype(str).max()).replace('-','')
    return None

def _params(params):
    out={}
    for k,v in params.items():
        if v in (None,'',[]): continue
        if isinstance(v,list) and k in ('symbol','index_symbol'): out[k+'_count']=len(v); out[k+'_sample']=v[:5]
        else: out[k]=v
    return out

class PandaDataSource:
    def __init__(self,retries=2): self.api=init_api(); self.retries=retries; self.calls=[]
    def call(self,method,required_columns=(),unsupported_hint=False,**params):
        fn:Callable|None=getattr(self.api,method,None); safe=_params(params)
        if fn is None:
            r=CallResult(method,'unsupported',params=safe,error='SDK不包含该方法'); self.calls.append(r); return r
        last=None
        for attempt in range(1,self.retries+1):
            try:
                raw=fn(**params); df=raw.copy() if isinstance(raw,pd.DataFrame) else pd.DataFrame(raw) if raw is not None else pd.DataFrame()
                missing=[c for c in required_columns if c not in df.columns]
                status='empty' if df.empty else 'error' if missing else 'ok'; error='接口成功但无记录' if df.empty else f'缺少必要字段: {", ".join(missing)}' if missing else None
                r=CallResult(method,status,df,len(df),[str(c) for c in df.columns],latest_date(df),safe,error,attempt); self.calls.append(r); return r
            except Exception as e: last=e
        text=safe_error(last or '未知错误'); unsupported=unsupported_hint and any(x in text.lower() for x in ('unsupported','not support','废弃','未上线','404'))
        r=CallResult(method,'unsupported' if unsupported else 'error',params=safe,error=text,attempts=self.retries); self.calls.append(r); return r
    def provenance(self): return [x.provenance() for x in self.calls]

def normalize_date(df):
    if 'date' in df.columns: df=df.copy(); df['date']=df['date'].astype(str).str.replace('-','',regex=False)
    return df

def fetch_windows(source,method,symbols,start,end,required=(),fields=None):
    start_dt=datetime.strptime(start,'%Y%m%d'); end_dt=datetime.strptime(end,'%Y%m%d'); chunks=[]; cur=start_dt
    while cur<=end_dt:
        chunk_end=min(cur+timedelta(days=364),end_dt)
        r=source.call(method,symbol=symbols,start_date=cur.strftime('%Y%m%d'),end_date=chunk_end.strftime('%Y%m%d'),fields=fields or [],required_columns=required,unsupported_hint=True)
        if r.ok: chunks.append(r.data)
        cur=chunk_end+timedelta(days=1)
    if not chunks: return CallResult(method,'empty',params={'symbol_count':len(symbols) if isinstance(symbols,list) else 1,'start_date':start,'end_date':end},error='分段查询未返回记录')
    df=pd.concat(chunks,ignore_index=True).drop_duplicates([c for c in ('symbol','date') if c in pd.concat(chunks,ignore_index=True).columns],keep='last'); df=normalize_date(df)
    return CallResult(method,'ok',df,len(df),[str(c) for c in df.columns],latest_date(df),{'symbol_count':len(symbols) if isinstance(symbols,list) else 1,'start_date':start,'end_date':end})

def fetch_etf_universe(source):
    # get_fund_detail rejects is_qdii_fund as a query parameter on the live
    # service; filter the returned metadata locally instead.
    return source.call('get_fund_detail',type='E',etf_lof_type='ETF',index_fund_type='I',status='L',fields=[])

def fetch_index_details(source): return source.call('get_index_detail',fields=[])

def fetch_product_bundle(source,symbol,as_of,years=3):
    start=(datetime.strptime(as_of,'%Y%m%d')-timedelta(days=365*years+30)).strftime('%Y%m%d')
    daily=fetch_windows(source,'get_fund_daily_post',[symbol],start,as_of,required=('symbol','date','close','pre_close'))
    raw=fetch_windows(source,'get_fund_daily',[symbol],start,as_of,required=('symbol','date','close','amount'))
    flow=fetch_windows(source,'get_fund_etf_cr_net',[symbol],start,as_of,required=('symbol','date','net_inflow','shares_change'),fields=[])
    cr=fetch_windows(source,'get_fund_etf_cr',[symbol],start,as_of,required=('symbol','date'),fields=[])
    basket=fetch_windows(source,'get_fund_etf_constituents',[symbol],start,as_of,required=('symbol','date','stock_symbol'),fields=[])
    return {'daily':daily,'raw':raw,'flow':flow,'cr':cr,'basket':basket}

def fetch_index_bundle(source,index_symbol,as_of,years=3):
    start=(datetime.strptime(as_of,'%Y%m%d')-timedelta(days=365*years+30)).strftime('%Y%m%d')
    return fetch_windows(source,'get_index_daily',[index_symbol],start,as_of,required=('symbol','date','close','pre_close'))
