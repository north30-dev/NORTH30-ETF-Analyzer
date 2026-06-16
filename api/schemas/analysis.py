# -*- coding: utf-8 -*-
"""分析相关 Pydantic 请求/响应模型"""

from typing import Optional
from pydantic import BaseModel, Field


class NavTrendRequest(BaseModel):
    """净值走势分析请求"""
    symbol: str = Field(..., description="ETF代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")


class RiskMetricsRequest(BaseModel):
    """风险指标计算请求"""
    symbol: str = Field(..., description="ETF代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")
    benchmark_symbol: Optional[str] = Field(None, description="基准指数代码")


class PerformanceRequest(BaseModel):
    """绩效分析请求"""
    symbol: str = Field(..., description="ETF代码")
    benchmark_symbol: str = Field(..., description="基准指数代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")


class HoldingsAnalysisRequest(BaseModel):
    """成分股分析请求"""
    symbol: str = Field(..., description="ETF代码")


class IndustryDistributionRequest(BaseModel):
    """行业分布统计请求"""
    symbol: str = Field(..., description="ETF代码")
