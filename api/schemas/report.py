# -*- coding: utf-8 -*-
"""报告相关 Pydantic 请求/响应模型"""

from typing import Optional, List
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """报告生成请求"""
    symbol: str = Field(..., description="ETF代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")
    benchmark_symbol: Optional[str] = Field(None, description="基准指数代码")
    modules: Optional[List[str]] = Field(None, description="报告模块列表")


class ReportTaskResponse(BaseModel):
    """报告任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field("PENDING", description="任务状态")


class ChartGenerateRequest(BaseModel):
    """图表生成请求"""
    symbol: str = Field(..., description="ETF代码")
    chart_type: str = Field(..., description="图表类型: kline, nav_trend, industry_pie, holdings_bar, drawdown")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")
