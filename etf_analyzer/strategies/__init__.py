# -*- coding: utf-8 -*-
"""
量化策略包

提供策略注册工厂机制，支持通过装饰器或函数调用方式注册和获取策略实例。
所有策略必须继承 BaseStrategy 抽象基类。
"""

from etf_analyzer.strategies.base import BaseStrategy
from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("strategies")

# 策略注册字典，键为策略名称，值为策略类
_STRATEGY_REGISTRY = {}


def register_strategy(name: str, cls: type = None):
    """注册策略到工厂字典，支持装饰器和函数调用两种方式。

    用法一（装饰器模式）：
        @register_strategy("momentum")
        class MomentumStrategy(BaseStrategy):
            ...

    用法二（函数调用模式）：
        register_strategy("momentum", MomentumStrategy)

    Args:
        name: 策略注册名称，用于后续获取策略实例
        cls: 策略类，装饰器模式下由 Python 自动传入

    Returns:
        装饰器模式下返回原类；函数调用模式下返回 None

    Raises:
        TypeError: cls 不是 BaseStrategy 的子类时抛出
        ValueError: 策略名称已被注册时抛出
    """
    def decorator(strategy_cls: type):
        if not issubclass(strategy_cls, BaseStrategy):
            raise TypeError(
                f"策略类 {strategy_cls.__name__} 必须继承 BaseStrategy"
            )
        if name in _STRATEGY_REGISTRY:
            raise ValueError(
                f"策略名称 '{name}' 已被注册，请使用其他名称"
            )
        _STRATEGY_REGISTRY[name] = strategy_cls
        logger.info("策略已注册: %s -> %s", name, strategy_cls.__name__)
        return strategy_cls

    if cls is not None:
        # 函数调用模式：register_strategy("momentum", MomentumStrategy)
        return decorator(cls)

    # 装饰器模式：@register_strategy("momentum")
    return decorator


def get_strategy(name: str, **params) -> BaseStrategy:
    """根据名称获取策略实例。

    Args:
        name: 已注册的策略名称
        **params: 传递给策略构造函数的参数

    Returns:
        BaseStrategy: 策略实例

    Raises:
        KeyError: 策略名称未注册时抛出
    """
    if name not in _STRATEGY_REGISTRY:
        available = ", ".join(_STRATEGY_REGISTRY.keys()) or "（无）"
        raise KeyError(
            f"策略 '{name}' 未注册，可用策略: {available}"
        )
    strategy_cls = _STRATEGY_REGISTRY[name]
    return strategy_cls(**params)


def list_strategies():
    """返回所有已注册策略的名称列表。

    Returns:
        list[str]: 已注册策略名称列表
    """
    return list(_STRATEGY_REGISTRY.keys())


__all__ = [
    "BaseStrategy",
    "register_strategy",
    "get_strategy",
    "list_strategies",
]
