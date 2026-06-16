# -*- coding: utf-8 -*-
"""分析计算 API 路由"""

from typing import Optional

from fastapi import APIRouter, Depends

from api.deps import get_analyzer
from api.schemas.etf import APIResponse
from api.schemas.analysis import (
    NavTrendRequest, RiskMetricsRequest, PerformanceRequest,
    HoldingsAnalysisRequest, IndustryDistributionRequest,
)
from etf_analyzer.core.analyzer import ETFAnalyzer

router = APIRouter(prefix="/analysis", tags=["分析计算"])


@router.post("/nav-trend", summary="净值走势分析")
def analyze_nav_trend(
    request: NavTrendRequest,
    analyzer: ETFAnalyzer = Depends(get_analyzer),
):
    """执行净值走势分析。"""
    result = analyzer.analyze_nav_trend(
        request.symbol, start_date=request.start_date, end_date=request.end_date,
    )
    if not result:
        return APIResponse(code=404, message="净值走势分析失败")
    # 移除不可序列化的 nav_data
    serializable = {k: v for k, v in result.items() if k != "nav_data"}
    return APIResponse(code=0, data=serializable)


@router.post("/risk-metrics", summary="风险指标计算")
def calculate_risk_metrics(
    request: RiskMetricsRequest,
    analyzer: ETFAnalyzer = Depends(get_analyzer),
):
    """计算风险指标。"""
    result = analyzer.calculate_risk_metrics(
        request.symbol, start_date=request.start_date, end_date=request.end_date,
        benchmark_symbol=request.benchmark_symbol,
    )
    if not result:
        return APIResponse(code=404, message="风险指标计算失败")
    return APIResponse(code=0, data=result)


@router.post("/performance", summary="绩效分析")
def analyze_performance(
    request: PerformanceRequest,
    analyzer: ETFAnalyzer = Depends(get_analyzer),
):
    """执行绩效分析。"""
    result = analyzer.analyze_performance(
        request.symbol, request.benchmark_symbol,
        start_date=request.start_date, end_date=request.end_date,
    )
    if not result:
        return APIResponse(code=404, message="绩效分析失败")
    return APIResponse(code=0, data=result)


@router.post("/holdings", summary="成分股构成分析")
def analyze_holdings(
    request: HoldingsAnalysisRequest,
    analyzer: ETFAnalyzer = Depends(get_analyzer),
):
    """执行成分股构成分析。"""
    result = analyzer.analyze_holdings(request.symbol)
    if not result:
        return APIResponse(code=404, message="成分股分析失败")
    serializable = {}
    for k, v in result.items():
        if hasattr(v, "to_dict"):
            serializable[k] = v.to_dict(orient="records")
        else:
            serializable[k] = v
    return APIResponse(code=0, data=serializable)


@router.post("/industry-distribution", summary="行业分布统计")
def analyze_industry_distribution(
    request: IndustryDistributionRequest,
    analyzer: ETFAnalyzer = Depends(get_analyzer),
):
    """执行行业分布统计。"""
    result = analyzer.analyze_industry_distribution(request.symbol)
    if not result:
        return APIResponse(code=404, message="行业分布统计失败")
    serializable = {}
    for k, v in result.items():
        if hasattr(v, "to_dict"):
            serializable[k] = v.to_dict(orient="records")
        else:
            serializable[k] = v
    return APIResponse(code=0, data=serializable)
