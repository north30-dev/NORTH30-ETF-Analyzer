# -*- coding: utf-8 -*-
"""策略相关 Pydantic 请求/响应模型"""

from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class StrategyInfo(BaseModel):
    """策略信息"""
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    default_params: Dict[str, Any] = Field(..., description="默认参数")


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: List[StrategyInfo] = Field(..., description="策略列表")


class StrategyParamsResponse(BaseModel):
    """策略参数响应"""
    strategy_name: str = Field(..., description="策略名称")
    params: Dict[str, Any] = Field(..., description="当前参数")
    param_descriptions: Dict[str, str] = Field(..., description="参数说明")


class UpdateStrategyParamsRequest(BaseModel):
    """更新策略参数请求"""
    params: Dict[str, Any] = Field(..., description="需要更新的参数字典")


class SignalRequest(BaseModel):
    """信号生成请求"""
    symbol: str = Field(..., description="ETF代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")
    data_source: Optional[str] = Field("api", description="数据源: api, csv, database")
    csv_path: Optional[str] = Field(None, description="CSV文件路径（data_source为csv时必填）")


class SignalData(BaseModel):
    """单条信号数据"""
    date: str = Field(..., description="日期")
    signal: int = Field(..., description="信号值: 1=买入, -1=卖出, 0=持有")
    position: float = Field(..., description="建议仓位比例 0.0~1.0")


class SignalResponse(BaseModel):
    """信号生成响应"""
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="ETF代码")
    signals: List[SignalData] = Field(..., description="信号列表")
    current_signal: Optional[Dict[str, Any]] = Field(None, description="当前信号详情")
