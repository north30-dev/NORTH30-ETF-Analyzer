# -*- coding: utf-8 -*-
"""回测相关 Pydantic 请求/响应模型"""

from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    """回测请求"""
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="ETF代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")
    initial_capital: Optional[float] = Field(1000000.0, description="初始资金")
    params: Optional[Dict[str, Any]] = Field(None, description="策略参数覆盖")
    commission_rate: Optional[float] = Field(0.0003, description="佣金费率")
    stamp_tax_rate: Optional[float] = Field(0.001, description="印花税率")
    slippage: Optional[float] = Field(0.001, description="滑点")


class PerformanceMetrics(BaseModel):
    """绩效指标"""
    total_return: float = Field(..., description="总收益率")
    annualized_return: float = Field(..., description="年化收益率")
    sharpe_ratio: float = Field(..., description="夏普比率")
    max_drawdown: float = Field(..., description="最大回撤")
    max_drawdown_duration: int = Field(..., description="最大回撤持续天数")
    win_rate: float = Field(..., description="胜率")
    profit_loss_ratio: float = Field(..., description="盈亏比")
    trade_count: int = Field(..., description="交易次数")
    calmar_ratio: float = Field(..., description="Calmar比率")


class BacktestSummaryResponse(BaseModel):
    """回测摘要响应"""
    backtest_id: str = Field(..., description="回测ID")
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="ETF代码")
    performance: PerformanceMetrics = Field(..., description="绩效指标")


class BacktestDetailResponse(BaseModel):
    """回测详情响应"""
    backtest_id: str = Field(..., description="回测ID")
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="ETF代码")
    performance: PerformanceMetrics = Field(..., description="绩效指标")
    trades: List[Dict[str, Any]] = Field(..., description="交易记录")
    equity_curve: List[Dict[str, Any]] = Field(..., description="净值曲线")


class CompareRequest(BaseModel):
    """多策略对比请求"""
    strategy_names: List[str] = Field(..., description="策略名称列表")
    symbol: str = Field(..., description="ETF代码")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")
    initial_capital: Optional[float] = Field(1000000.0, description="初始资金")


class CompareResponse(BaseModel):
    """多策略对比响应"""
    results: Dict[str, PerformanceMetrics] = Field(..., description="各策略绩效指标")


class OptimizeRequest(BaseModel):
    """参数寻优请求"""
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="ETF代码")
    param_grid: Dict[str, List[Any]] = Field(..., description="参数网格")
    start_date: Optional[str] = Field(None, description="起始日期(YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="结束日期(YYYYMMDD)")
    metric: Optional[str] = Field("sharpe_ratio", description="排序指标")
    top_n: Optional[int] = Field(5, description="返回前N个最优结果")


class OptimizeResponse(BaseModel):
    """参数寻优响应"""
    best_params: Dict[str, Any] = Field(..., description="最优参数")
    best_metric_value: float = Field(..., description="最优指标值")
    top_results: List[Dict[str, Any]] = Field(..., description="Top N结果")
    total_combinations: int = Field(..., description="总参数组合数")


class BacktestHistoryItem(BaseModel):
    """回测历史条目"""
    backtest_id: str = Field(..., description="回测ID")
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="ETF代码")
    created_at: str = Field(..., description="创建时间")
    total_return: float = Field(..., description="总收益率")


class BacktestHistoryResponse(BaseModel):
    """回测历史响应"""
    history: List[BacktestHistoryItem] = Field(..., description="回测历史列表")
