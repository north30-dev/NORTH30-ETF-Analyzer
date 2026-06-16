# -*- coding: utf-8 -*-
"""ETF 相关 Pydantic 请求/响应模型"""

from typing import Optional, List
from pydantic import BaseModel, Field


class ETFListRequest(BaseModel):
    """ETF 列表查询请求"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(20, ge=1, le=100, description="每页记录数")


class RealtimeQuoteResponse(BaseModel):
    """实时行情响应"""
    symbol: str = Field(..., description="ETF代码")
    name: str = Field("", description="ETF名称")
    price: float = Field(0, description="最新价")
    change_pct: float = Field(0, description="涨跌幅")
    change_amt: float = Field(0, description="涨跌额")
    open: float = Field(0, description="开盘价")
    high: float = Field(0, description="最高价")
    low: float = Field(0, description="最低价")
    prev_close: float = Field(0, description="昨收价")
    volume: float = Field(0, description="成交量")
    amount: float = Field(0, description="成交额")


class HistoryDataRequest(BaseModel):
    """历史数据查询请求"""
    symbol: str = Field(..., description="ETF代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")


class HoldingsResponse(BaseModel):
    """持仓信息响应"""
    symbol: str = Field(..., description="ETF代码")
    holdings: list = Field(default_factory=list, description="持仓列表")


class APIResponse(BaseModel):
    """通用 API 响应"""
    code: int = Field(0, description="状态码，0表示成功")
    message: str = Field("success", description="响应消息")
    data: Optional[dict | list] = Field(None, description="响应数据")
