# -*- coding: utf-8 -*-
"""
测试公共 fixtures 模块

为所有测试提供共享的示例数据，包括历史行情 DataFrame、持仓数据 DataFrame
和实时行情字典，避免每个测试文件重复构造数据。
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_history_df():
    """示例历史行情数据 DataFrame。

    包含日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率列，
    共 30 条数据。收盘价在 1~5 之间，涨跌幅在 -5%~5% 之间。
    """
    np.random.seed(42)
    n = 30
    dates = pd.bdate_range(start="2024-01-02", periods=n)

    # 以 3.0 为基准，模拟收盘价在 1~5 之间波动
    close_prices = 3.0 + np.cumsum(np.random.uniform(-0.1, 0.1, n))
    close_prices = np.clip(close_prices, 1.0, 5.0)

    # 涨跌幅在 -5%~5% 之间
    change_pcts = np.random.uniform(-5.0, 5.0, n)
    change_amts = close_prices * change_pcts / 100

    # 开盘价在收盘价附近小幅波动
    open_prices = close_prices + np.random.uniform(-0.05, 0.05, n)
    open_prices = np.clip(open_prices, 1.0, 5.0)

    # 最高价 >= max(开盘, 收盘)，最低价 <= min(开盘, 收盘)
    high_prices = np.maximum(open_prices, close_prices) + np.random.uniform(
        0.01, 0.1, n
    )
    low_prices = np.minimum(open_prices, close_prices) - np.random.uniform(
        0.01, 0.1, n
    )
    low_prices = np.clip(low_prices, 0.5, 5.0)

    # 成交量和成交额
    volumes = np.random.randint(100000, 1000000, n).astype(float)
    amounts = volumes * close_prices

    # 振幅
    amplitudes = (high_prices - low_prices) / close_prices * 100

    # 换手率
    turnover_rates = np.random.uniform(0.1, 5.0, n)

    df = pd.DataFrame(
        {
            "日期": dates,
            "开盘": np.round(open_prices, 4),
            "收盘": np.round(close_prices, 4),
            "最高": np.round(high_prices, 4),
            "最低": np.round(low_prices, 4),
            "成交量": volumes,
            "成交额": np.round(amounts, 2),
            "振幅": np.round(amplitudes, 4),
            "涨跌幅": np.round(change_pcts, 4),
            "涨跌额": np.round(change_amts, 4),
            "换手率": np.round(turnover_rates, 4),
        }
    )
    return df


@pytest.fixture
def sample_holdings_df():
    """示例持仓数据 DataFrame。

    包含股票代码、股票名称、持仓占比列，共 15 条数据。
    持仓占比合计接近 100%。
    """
    data = [
        ("600519", "贵州茅台", 5.82),
        ("000858", "五粮液", 4.35),
        ("600036", "招商银行", 4.12),
        ("601318", "中国平安", 3.98),
        ("000333", "美的集团", 3.56),
        ("600276", "恒瑞医药", 3.21),
        ("601888", "中国中免", 2.95),
        ("000651", "格力电器", 2.78),
        ("600030", "中信证券", 2.65),
        ("601166", "兴业银行", 2.43),
        ("600887", "伊利股份", 2.31),
        ("000568", "泸州老窖", 2.18),
        ("601398", "工商银行", 2.05),
        ("600000", "浦发银行", 1.92),
        ("000002", "万科A", 1.78),
    ]
    df = pd.DataFrame(data, columns=["股票代码", "股票名称", "占净值比例"])
    return df


@pytest.fixture
def sample_realtime_data():
    """示例实时行情字典。

    包含 symbol、name、price、change_pct、change_amt、volume、amount、
    open、high、low、prev_close 等键，价格在 1~5 之间，涨跌幅在 -5%~5% 之间。
    """
    return {
        "symbol": "510300",
        "name": "沪深300ETF",
        "price": 3.856,
        "change_pct": 1.23,
        "change_amt": 0.047,
        "volume": 12345678.0,
        "amount": 47654321.0,
        "open": 3.812,
        "high": 3.878,
        "low": 3.798,
        "prev_close": 3.809,
    }
