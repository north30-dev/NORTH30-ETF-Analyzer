# -*- coding: utf-8 -*-
"""回测管理 API 路由"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from api.schemas.etf import APIResponse
from api.schemas.backtest import (
    BacktestRequest, PerformanceMetrics,
    BacktestSummaryResponse, BacktestDetailResponse,
    CompareRequest, CompareResponse,
    OptimizeRequest, OptimizeResponse,
    BacktestHistoryItem, BacktestHistoryResponse,
)
from etf_analyzer.strategies import get_strategy, list_strategies
from etf_analyzer.backtest.data_loader import BacktestDataLoader
from etf_analyzer.backtest.engine import BacktestEngine
from etf_analyzer.backtest.optimizer import GridSearchOptimizer

router = APIRouter(prefix="/backtest", tags=["回测管理"])

# 回测结果内存缓存，键为 backtest_id，值为回测详情字典
_backtest_cache: dict = {}

# 回测历史记录列表
_backtest_history: list = []

# 数据加载器实例
_data_loader = BacktestDataLoader()


def _load_data(symbol: str, start_date: str = None, end_date: str = None):
    """加载行情数据，优先使用API，失败时回退到数据库。"""
    data = _data_loader.load_from_api(symbol, start_date=start_date,
                                      end_date=end_date)
    if data.empty:
        data = _data_loader.load_from_database(symbol, start_date=start_date,
                                                end_date=end_date)
    return data


def _performance_to_metrics(performance: dict) -> PerformanceMetrics:
    """将引擎返回的绩效字典转换为 PerformanceMetrics 模型。"""
    return PerformanceMetrics(
        total_return=performance.get("total_return", 0.0),
        annualized_return=performance.get("annualized_return", 0.0),
        sharpe_ratio=performance.get("sharpe_ratio", 0.0),
        max_drawdown=performance.get("max_drawdown", 0.0),
        max_drawdown_duration=performance.get("max_drawdown_duration", 0),
        win_rate=performance.get("win_rate", 0.0),
        profit_loss_ratio=performance.get("profit_loss_ratio", 0.0),
        trade_count=performance.get("trade_count", 0),
        calmar_ratio=performance.get("calmar_ratio", 0.0),
    )


def _save_backtest_result(backtest_id: str, strategy_name: str, symbol: str,
                          result, performance: PerformanceMetrics):
    """保存回测结果到内存缓存和历史记录。"""
    # 将交易记录和净值曲线转换为可序列化格式
    trades_list = []
    if hasattr(result.trades, "to_dict"):
        trades_list = result.trades.to_dict(orient="records")
    elif isinstance(result.trades, list):
        trades_list = result.trades

    equity_list = []
    if hasattr(result.equity_curve, "to_dict"):
        equity_list = result.equity_curve.to_dict(orient="records")
    elif isinstance(result.equity_curve, list):
        equity_list = result.equity_curve

    # 处理日期类型不可序列化的问题
    for record in trades_list:
        for key, value in record.items():
            if hasattr(value, "strftime"):
                record[key] = value.strftime("%Y-%m-%d")
            elif hasattr(value, "item"):
                record[key] = value.item()

    for record in equity_list:
        for key, value in record.items():
            if hasattr(value, "strftime"):
                record[key] = value.strftime("%Y-%m-%d")
            elif hasattr(value, "item"):
                record[key] = value.item()

    detail = BacktestDetailResponse(
        backtest_id=backtest_id,
        strategy_name=strategy_name,
        symbol=symbol,
        performance=performance,
        trades=trades_list,
        equity_curve=equity_list,
    )

    _backtest_cache[backtest_id] = detail

    # 添加到历史记录
    _backtest_history.append(BacktestHistoryItem(
        backtest_id=backtest_id,
        strategy_name=strategy_name,
        symbol=symbol,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_return=performance.total_return,
    ))


@router.post("/run", summary="执行回测")
def run_backtest(request: BacktestRequest):
    """执行单策略回测，返回回测ID和摘要结果。"""
    # 验证策略是否存在
    try:
        strategy = get_strategy(request.strategy_name,
                                **(request.params or {}))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 加载数据
    data = _load_data(request.symbol, request.start_date, request.end_date)
    if data.empty:
        raise HTTPException(
            status_code=400,
            detail=f"数据加载失败，代码: {request.symbol}",
        )

    # 创建回测引擎并执行
    engine = BacktestEngine(
        commission_rate=request.commission_rate,
        stamp_tax_rate=request.stamp_tax_rate,
        slippage=request.slippage,
    )
    result = engine.run(strategy, data, request.initial_capital)

    # 生成回测ID并缓存结果
    backtest_id = str(uuid.uuid4())
    performance = _performance_to_metrics(result.performance)
    _save_backtest_result(backtest_id, request.strategy_name,
                          request.symbol, result, performance)

    return APIResponse(code=0, data=BacktestSummaryResponse(
        backtest_id=backtest_id,
        strategy_name=request.strategy_name,
        symbol=request.symbol,
        performance=performance,
    ).model_dump())


@router.get("/{backtest_id}/result", summary="查询回测结果")
def get_backtest_result(backtest_id: str):
    """根据回测ID查询回测详情。"""
    if backtest_id not in _backtest_cache:
        raise HTTPException(status_code=404, detail="回测记录不存在")
    return APIResponse(code=0, data=_backtest_cache[backtest_id].model_dump())


@router.post("/compare", summary="多策略对比")
def compare_strategies(request: CompareRequest):
    """对多个策略执行对比回测。"""
    # 验证策略是否存在
    strategies = []
    for name in request.strategy_names:
        try:
            strategy = get_strategy(name)
            strategies.append(strategy)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # 加载数据
    data = _load_data(request.symbol, request.start_date, request.end_date)
    if data.empty:
        raise HTTPException(
            status_code=400,
            detail=f"数据加载失败，代码: {request.symbol}",
        )

    # 执行对比回测
    engine = BacktestEngine()
    comparison_results = engine.run_comparison(
        strategies, data, request.initial_capital,
    )

    # 转换结果格式
    results = {}
    for name, bt_result in comparison_results.items():
        results[name] = _performance_to_metrics(bt_result.performance)

    return APIResponse(code=0, data=CompareResponse(
        results=results,
    ).model_dump())


@router.post("/optimize", summary="参数寻优")
def optimize_params(request: OptimizeRequest):
    """对指定策略执行网格搜索参数寻优。"""
    # 验证策略是否存在，获取策略类
    try:
        # 先创建一个实例以验证策略可用
        test_instance = get_strategy(request.strategy_name)
        strategy_cls = type(test_instance)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 加载数据
    data = _load_data(request.symbol, request.start_date, request.end_date)
    if data.empty:
        raise HTTPException(
            status_code=400,
            detail=f"数据加载失败，代码: {request.symbol}",
        )

    # 创建回测引擎和寻优器
    engine = BacktestEngine()
    optimizer = GridSearchOptimizer(engine=engine)

    try:
        opt_result = optimizer.optimize(
            strategy_cls, data, request.param_grid,
            metric=request.metric, top_n=request.top_n,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 转换 Top N 结果为可序列化格式
    top_results = []
    for params, metric_value, bt_result in opt_result.top_results:
        item = {
            "params": params,
            "metric_value": metric_value,
        }
        # 如果是引擎的 BacktestResult，提取绩效指标
        if hasattr(bt_result, "performance"):
            item["performance"] = bt_result.performance
        elif hasattr(bt_result, "total_return"):
            # optimizer 内置的 BacktestResult
            item["performance"] = {
                "total_return": bt_result.total_return,
                "annual_return": bt_result.annual_return,
                "sharpe_ratio": bt_result.sharpe_ratio,
                "max_drawdown": bt_result.max_drawdown,
                "win_rate": bt_result.win_rate,
                "profit_loss_ratio": bt_result.profit_loss_ratio,
                "trade_count": bt_result.trade_count,
            }
        top_results.append(item)

    return APIResponse(code=0, data=OptimizeResponse(
        best_params=opt_result.best_params,
        best_metric_value=opt_result.best_metric_value,
        top_results=top_results,
        total_combinations=opt_result.total_combinations,
    ).model_dump())


@router.get("/history", summary="获取回测历史")
def get_backtest_history():
    """获取所有回测历史记录。"""
    # 按创建时间倒序排列
    history = sorted(
        _backtest_history,
        key=lambda x: x.created_at,
        reverse=True,
    )
    return APIResponse(code=0, data=BacktestHistoryResponse(
        history=history,
    ).model_dump())
