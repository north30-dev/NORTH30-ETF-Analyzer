# -*- coding: utf-8 -*-
"""
网格搜索参数寻优模块

提供 GridSearchOptimizer 类，通过穷举参数网格的所有组合，
对策略进行回测并按指定指标排序，找出最优参数配置。
"""

import itertools
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("backtest.optimizer")


@dataclass
class BacktestResult:
    """回测结果数据类。

    封装单次回测的完整输出，包括绩效指标和交易记录。

    Attributes:
        total_return: 总收益率
        annual_return: 年化收益率
        max_drawdown: 最大回撤
        sharpe_ratio: 夏普比率
        win_rate: 胜率
        profit_loss_ratio: 盈亏比
        trade_count: 交易次数
        initial_capital: 初始资金
        final_capital: 最终资金
        trades: 交易记录列表，每条记录为字典
        equity_curve: 权益曲线 DataFrame
    """

    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    trade_count: int = 0
    initial_capital: float = 0.0
    final_capital: float = 0.0
    trades: list = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)

    def get_metric(self, metric_name: str) -> float:
        """根据指标名称获取对应的指标值。

        Args:
            metric_name: 指标名称，如 "sharpe_ratio"、"total_return" 等

        Returns:
            float: 指标值，指标不存在时返回 0.0
        """
        return getattr(self, metric_name, 0.0)


@dataclass
class OptimizationResult:
    """参数寻优结果。

    Attributes:
        best_params: 最优参数字典
        best_metric_value: 最优指标值
        best_result: 最优回测结果
        top_results: Top N 结果列表，每项为 (params, metric_value, BacktestResult) 元组
        total_combinations: 总参数组合数
    """

    best_params: dict
    best_metric_value: float
    best_result: BacktestResult
    top_results: list
    total_combinations: int


def create_param_range(start, end, step):
    """生成参数范围列表。

    根据步长类型自动判断生成整数列表或浮点列表：
    - 整数步长 → 生成整数列表
    - 浮点步长 → 生成浮点列表

    Args:
        start: 起始值
        end: 结束值（包含）
        step: 步长

    Returns:
        list: 参数值列表

    Examples:
        >>> create_param_range(10, 30, 10)
        [10, 20, 30]
        >>> create_param_range(0.01, 0.03, 0.01)
        [0.01, 0.02, 0.03]
    """
    if isinstance(step, float) or isinstance(start, float) or isinstance(end, float):
        # 浮点步长：使用循环累加避免浮点精度问题
        result = []
        current = start
        while current <= end + step * 1e-9:
            result.append(round(current, 10))
            current += step
        return result
    else:
        # 整数步长
        return list(range(start, end + 1, step))


class GridSearchOptimizer:
    """网格搜索参数寻优器。

    通过穷举参数网格的所有组合，对每组参数执行回测，
    并按指定指标排序返回最优结果。

    支持两种参数网格格式：
    - 列表形式：{"period": [10, 20, 30]}
    - 范围形式：使用 create_param_range() 生成列表后传入
    """

    def __init__(self, engine=None):
        """初始化网格搜索寻优器。

        Args:
            engine: BacktestEngine 实例，如果为 None 则使用内置简易回测逻辑
        """
        self.engine = engine

    def optimize(self, strategy_class, data, param_grid,
                 metric="sharpe_ratio", top_n=5,
                 initial_capital=1000000.0) -> OptimizationResult:
        """执行网格搜索参数寻优。

        对参数网格中的所有组合逐一回测，按指定指标降序排序，
        返回最优参数及 Top N 结果。

        Args:
            strategy_class: 策略类（不是实例），需继承 BaseStrategy
            data: 标准OHLCV DataFrame
            param_grid: 参数网格字典，如 {"period": [10, 20, 30]}
            metric: 排序指标名称，默认 "sharpe_ratio"
            top_n: 返回前N个最优结果，默认5
            initial_capital: 初始资金，默认100万

        Returns:
            OptimizationResult: 寻优结果

        Raises:
            ValueError: 参数网格为空时抛出
        """
        if not param_grid:
            raise ValueError("参数网格不能为空")

        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        total_combinations = len(combinations)

        logger.info("开始网格搜索，共 %d 组参数组合，排序指标: %s",
                     total_combinations, metric)

        # 逐一回测每组参数
        results = []
        for i, combo in enumerate(combinations, 1):
            params = dict(zip(param_names, combo))

            try:
                # 创建策略实例
                strategy = strategy_class(**params)

                # 执行回测
                backtest_result = self._run_backtest(
                    strategy, data, initial_capital
                )

                # 提取指标值
                metric_value = backtest_result.get_metric(metric)

                results.append((params, metric_value, backtest_result))

                if i % 10 == 0 or i == total_combinations:
                    logger.info("已完成 %d/%d 组参数组合", i, total_combinations)

            except Exception as e:
                logger.warning("参数组合 %s 回测失败: %s", params, e)
                continue

        if not results:
            raise RuntimeError("所有参数组合回测均失败，无有效结果")

        # 按指标值降序排序
        results.sort(key=lambda x: x[1], reverse=True)

        # 取 Top N
        top_results = results[:top_n]

        # 最优结果
        best_params = top_results[0][0]
        best_metric_value = top_results[0][1]
        best_result = top_results[0][2]

        logger.info("网格搜索完成，最优参数: %s，%s: %.4f",
                     best_params, metric, best_metric_value)

        return OptimizationResult(
            best_params=best_params,
            best_metric_value=best_metric_value,
            best_result=best_result,
            top_results=top_results,
            total_combinations=total_combinations,
        )

    def _run_backtest(self, strategy, data, initial_capital):
        """执行单次回测。

        如果配置了外部回测引擎则使用引擎执行，否则使用内置简易回测逻辑。

        Args:
            strategy: 策略实例
            data: 标准OHLCV DataFrame
            initial_capital: 初始资金

        Returns:
            BacktestResult: 回测结果
        """
        if self.engine is not None:
            return self.engine.run(strategy, data, initial_capital)

        # 内置简易回测逻辑
        return self._simple_backtest(strategy, data, initial_capital)

    @staticmethod
    def _simple_backtest(strategy, data, initial_capital):
        """内置简易回测逻辑。

        根据策略生成的信号模拟交易，计算各项绩效指标。
        买入信号时全仓买入，卖出信号时全仓卖出，持有信号时维持仓位。

        Args:
            strategy: 策略实例
            data: 标准OHLCV DataFrame
            initial_capital: 初始资金

        Returns:
            BacktestResult: 回测结果
        """
        # 生成交易信号
        signals = strategy.generate_signals(data)

        # 合并价格数据和信号
        merged = data.copy()
        merged = merged.merge(signals[["date", "signal", "position"]],
                              on="date", how="left")
        merged["signal"] = merged["signal"].fillna(0)
        merged["position"] = merged["position"].fillna(0.0)

        # 模拟交易
        capital = initial_capital
        shares = 0
        trades = []
        equity_curve_data = []

        for _, row in merged.iterrows():
            price = row["close"]
            signal = int(row["signal"])
            position = float(row["position"])

            # 买入信号且当前无持仓
            if signal == 1 and shares == 0 and position > 0:
                buy_shares = int(capital * position / price)
                if buy_shares > 0:
                    cost = buy_shares * price
                    capital -= cost
                    shares = buy_shares
                    trades.append({
                        "date": row["date"],
                        "action": "buy",
                        "price": price,
                        "shares": shares,
                        "cost": cost,
                    })

            # 卖出信号且当前有持仓
            elif signal == -1 and shares > 0:
                revenue = shares * price
                capital += revenue
                trades.append({
                    "date": row["date"],
                    "action": "sell",
                    "price": price,
                    "shares": shares,
                    "revenue": revenue,
                })
                shares = 0

            # 记录每日权益
            total_equity = capital + shares * price
            equity_curve_data.append({
                "date": row["date"],
                "equity": total_equity,
            })

        # 最后一天如果仍有持仓，按收盘价清仓计算
        final_capital = capital + shares * merged.iloc[-1]["close"]

        # 构建权益曲线
        equity_curve = pd.DataFrame(equity_curve_data)

        # 计算绩效指标
        total_return = (final_capital - initial_capital) / initial_capital

        # 年化收益率
        trading_days = len(merged)
        annual_return = (
            (1 + total_return) ** (252 / max(trading_days, 1)) - 1
            if total_return > -1 else -1.0
        )

        # 最大回撤
        max_drawdown = 0.0
        if not equity_curve.empty:
            equity_values = equity_curve["equity"].values
            peak = equity_values[0]
            for val in equity_values:
                if val > peak:
                    peak = val
                drawdown = (peak - val) / peak if peak > 0 else 0.0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # 夏普比率（假设无风险利率为0）
        sharpe_ratio = 0.0
        if not equity_curve.empty and len(equity_curve) > 1:
            daily_returns = equity_curve["equity"].pct_change().dropna()
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                sharpe_ratio = daily_returns.mean() / daily_returns.std() * (252 ** 0.5)

        # 胜率和盈亏比
        win_count = 0
        loss_count = 0
        total_profit = 0.0
        total_loss = 0.0
        buy_trade = None

        for trade in trades:
            if trade["action"] == "buy":
                buy_trade = trade
            elif trade["action"] == "sell" and buy_trade is not None:
                profit = trade["revenue"] - buy_trade["cost"]
                if profit > 0:
                    win_count += 1
                    total_profit += profit
                else:
                    loss_count += 1
                    total_loss += abs(profit)
                buy_trade = None

        total_closed = win_count + loss_count
        win_rate = win_count / total_closed if total_closed > 0 else 0.0
        avg_loss = total_loss / loss_count if loss_count > 0 else 1.0
        profit_loss_ratio = (total_profit / win_count) / avg_loss if win_count > 0 else 0.0

        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            trade_count=len(trades),
            initial_capital=initial_capital,
            final_capital=final_capital,
            trades=trades,
            equity_curve=equity_curve,
        )
