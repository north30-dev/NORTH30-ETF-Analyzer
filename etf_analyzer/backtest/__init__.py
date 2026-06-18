# -*- coding: utf-8 -*-
"""
回测模块

提供ETF策略回测相关功能，包括数据加载、策略执行和结果分析。
"""

from etf_analyzer.backtest.data_loader import BacktestDataLoader
from etf_analyzer.backtest.engine import BacktestEngine, BacktestResult
from etf_analyzer.backtest.optimizer import (
    GridSearchOptimizer,
    OptimizationResult,
    create_param_range,
)

__all__ = [
    "BacktestDataLoader",
    "BacktestEngine",
    "BacktestResult",
    "GridSearchOptimizer",
    "OptimizationResult",
    "create_param_range",
]
