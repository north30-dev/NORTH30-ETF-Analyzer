# -*- coding: utf-8 -*-
"""策略管理 API 路由"""

from fastapi import APIRouter, HTTPException

from api.schemas.etf import APIResponse
from api.schemas.strategy import (
    StrategyInfo, StrategyListResponse,
    StrategyParamsResponse, UpdateStrategyParamsRequest,
    SignalRequest, SignalData, SignalResponse,
)
from etf_analyzer.strategies import get_strategy, list_strategies
from etf_analyzer.backtest.data_loader import BacktestDataLoader
from etf_analyzer.backtest.signals import SignalGenerator

router = APIRouter(prefix="/strategy", tags=["策略管理"])

# 策略实例缓存，键为策略名称，值为策略实例
_strategy_cache: dict = {}

# 信号生成器实例
_signal_generator = SignalGenerator()

# 数据加载器实例
_data_loader = BacktestDataLoader()


def _get_or_create_strategy(name: str, **params):
    """获取或创建策略实例，带缓存。"""
    cache_key = (name, tuple(sorted(params.items())))
    if cache_key not in _strategy_cache:
        _strategy_cache[cache_key] = get_strategy(name, **params)
    return _strategy_cache[cache_key]


@router.get("/list", summary="获取策略列表")
def list_all_strategies():
    """获取所有已注册策略的列表。"""
    names = list_strategies()
    strategies = []
    for name in names:
        try:
            # 使用默认参数创建实例以获取描述信息
            instance = get_strategy(name)
            strategies.append(StrategyInfo(
                name=name,
                description=instance.get_description(),
                default_params=instance.get_parameters(),
            ))
        except Exception:
            # 策略创建失败时仍返回基本信息
            strategies.append(StrategyInfo(
                name=name,
                description="",
                default_params={},
            ))
    return APIResponse(code=0, data=StrategyListResponse(
        strategies=strategies,
    ).model_dump())


@router.get("/{strategy_name}/params", summary="获取策略参数")
def get_strategy_params(strategy_name: str):
    """获取指定策略的当前参数及参数说明。"""
    try:
        instance = get_strategy(strategy_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 构建参数说明，从策略实例的默认参数中提取
    params = instance.get_parameters()
    param_descriptions = {k: f"策略参数: {k}" for k in params}

    return APIResponse(code=0, data=StrategyParamsResponse(
        strategy_name=strategy_name,
        params=params,
        param_descriptions=param_descriptions,
    ).model_dump())


@router.put("/{strategy_name}/params", summary="更新策略参数")
def update_strategy_params(strategy_name: str, request: UpdateStrategyParamsRequest):
    """更新指定策略的参数。"""
    try:
        instance = get_strategy(strategy_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        instance.set_parameters(request.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数验证失败: {e}")

    # 清除该策略的缓存，下次请求时重新创建
    keys_to_remove = [
        k for k in _strategy_cache if k[0] == strategy_name
    ]
    for k in keys_to_remove:
        del _strategy_cache[k]

    return APIResponse(code=0, data=StrategyParamsResponse(
        strategy_name=strategy_name,
        params=instance.get_parameters(),
        param_descriptions={k: f"策略参数: {k}" for k in instance.get_parameters()},
    ).model_dump())


@router.post("/{strategy_name}/signals", summary="生成交易信号")
def generate_signals(strategy_name: str, request: SignalRequest):
    """根据策略生成交易信号。"""
    try:
        instance = get_strategy(strategy_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 根据数据源加载数据
    data = _load_data(request)
    if data.empty:
        raise HTTPException(
            status_code=400,
            detail=f"数据加载失败，代码: {request.symbol}",
        )

    # 生成信号
    signals_df = instance.generate_signals(data)
    if signals_df.empty:
        return APIResponse(code=0, data=SignalResponse(
            strategy_name=strategy_name,
            symbol=request.symbol,
            signals=[],
            current_signal=None,
        ).model_dump())

    # 转换信号数据为响应格式
    signal_list = []
    for _, row in signals_df.iterrows():
        date_val = row["date"]
        if hasattr(date_val, "strftime"):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            date_str = str(date_val)
        signal_list.append(SignalData(
            date=date_str,
            signal=int(row["signal"]),
            position=float(row["position"]),
        ))

    # 获取当前信号详情
    current_signal = _signal_generator.generate_signal(instance, data)

    return APIResponse(code=0, data=SignalResponse(
        strategy_name=strategy_name,
        symbol=request.symbol,
        signals=signal_list,
        current_signal=current_signal,
    ).model_dump())


def _load_data(request: SignalRequest):
    """根据请求数据源加载行情数据。"""
    source = request.data_source or "api"
    if source == "csv":
        if not request.csv_path:
            raise HTTPException(
                status_code=400,
                detail="使用CSV数据源时必须提供csv_path参数",
            )
        return _data_loader.load_from_csv(request.csv_path)
    elif source == "database":
        return _data_loader.load_from_database(
            request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    else:
        # 默认使用API数据源
        return _data_loader.load_from_api(
            request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
        )
