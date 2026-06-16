# -*- coding: utf-8 -*-
"""ETF 数据查询 API 路由"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps import get_fetcher
from api.schemas.etf import APIResponse
from etf_analyzer.core.data_fetcher import ETFDataFetcher

router = APIRouter(prefix="/etf", tags=["ETF数据查询"])


@router.get("/list", summary="查询ETF列表")
def get_etf_list(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    fetcher: ETFDataFetcher = Depends(get_fetcher),
):
    """查询ETF列表，支持关键词搜索和分页。"""
    df = fetcher.get_etf_list(keyword=keyword)
    if df is None or df.empty:
        return APIResponse(code=0, message="未找到数据", data=[])
    items = df.to_dict(orient="records")
    return APIResponse(code=0, data=items[skip:skip + limit])


@router.get("/{symbol}/quote", summary="获取ETF实时行情")
def get_realtime_quote(
    symbol: str,
    fetcher: ETFDataFetcher = Depends(get_fetcher),
):
    """获取指定ETF的实时行情数据。"""
    quote = fetcher.get_realtime_quote(symbol)
    if not quote:
        return APIResponse(code=404, message=f"未找到代码 {symbol} 的行情数据")
    return APIResponse(code=0, data=quote)


@router.get("/{symbol}/history", summary="获取ETF历史数据")
def get_history_data(
    symbol: str,
    start_date: Optional[str] = Query(None, description="起始日期(YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="结束日期(YYYYMMDD)"),
    fetcher: ETFDataFetcher = Depends(get_fetcher),
):
    """获取指定ETF的历史K线数据。"""
    df = fetcher.get_history_data(symbol, start_date=start_date, end_date=end_date)
    if df is None or df.empty:
        return APIResponse(code=404, message=f"未获取到 {symbol} 的历史数据")
    return APIResponse(code=0, data=df.to_dict(orient="records"))


@router.get("/{symbol}/holdings", summary="获取ETF持仓信息")
def get_etf_holdings(
    symbol: str,
    fetcher: ETFDataFetcher = Depends(get_fetcher),
):
    """获取指定ETF的持仓信息。"""
    df = fetcher.get_etf_holdings(symbol)
    if df is None or df.empty:
        return APIResponse(code=404, message=f"未获取到 {symbol} 的持仓信息")
    return APIResponse(code=0, data=df.to_dict(orient="records"))
