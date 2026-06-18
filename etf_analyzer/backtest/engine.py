# -*- coding: utf-8 -*-
"""
回测引擎模块

提供策略回测执行和绩效评估功能，支持单策略回测和多策略对比回测。
逐日模拟交易过程，计算各项绩效指标。
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config import RISK_FREE_RATE
from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("backtest.engine")


@dataclass
class BacktestResult:
    """回测结果。"""

    strategy_name: str
    performance: dict          # 绩效指标
    trades: pd.DataFrame       # 交易记录
    equity_curve: pd.DataFrame # 每日净值曲线
    positions: pd.DataFrame    # 持仓变化记录

    def get_metric(self, metric_name: str) -> float:
        """根据指标名称获取对应的绩效指标值。

        兼容 GridSearchOptimizer 的指标查询接口。

        Args:
            metric_name: 指标名称，如 "sharpe_ratio"、"total_return" 等

        Returns:
            float: 指标值，指标不存在时返回 0.0
        """
        return self.performance.get(metric_name, 0.0)


class BacktestEngine:
    """回测引擎，支持策略回测和绩效评估。"""

    def __init__(self, commission_rate=0.0003, stamp_tax_rate=0.001,
                 slippage=0.001):
        """
        Args:
            commission_rate: 佣金费率，默认万三
            stamp_tax_rate: 印花税率（仅卖出），默认千一
            slippage: 滑点，默认0.1%
        """
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage = slippage

    def run(self, strategy, data, initial_capital=1000000.0):
        """执行单策略回测。

        Args:
            strategy: BaseStrategy 实例
            data: 标准OHLCV DataFrame（列：date, open, high, low, close, volume）
            initial_capital: 初始资金，默认100万

        Returns:
            BacktestResult 回测结果对象
        """
        strategy_name = strategy.get_name()
        logger.info("开始回测策略: %s，初始资金: %.2f", strategy_name,
                     initial_capital)

        # 生成交易信号
        signals = strategy.generate_signals(data)
        if signals.empty:
            logger.warning("策略 %s 未生成任何信号", strategy_name)
            return self._build_empty_result(strategy_name, data,
                                            initial_capital)

        # 将信号与行情数据合并
        merged = self._merge_data_signals(data, signals)
        if merged.empty:
            logger.warning("策略 %s 信号与数据合并后为空", strategy_name)
            return self._build_empty_result(strategy_name, data,
                                            initial_capital)

        # 逐日模拟交易
        trades, equity_curve, positions = self._simulate(
            merged, initial_capital
        )

        # 计算绩效指标
        performance = self._calculate_performance(
            equity_curve, trades, initial_capital
        )

        logger.info("回测完成，策略: %s，总收益率: %.2f%%",
                     strategy_name, performance["total_return"] * 100)

        return BacktestResult(
            strategy_name=strategy_name,
            performance=performance,
            trades=trades,
            equity_curve=equity_curve,
            positions=positions,
        )

    def run_comparison(self, strategies, data, initial_capital=1000000.0):
        """多策略对比回测。

        Args:
            strategies: 策略实例列表
            data: 标准OHLCV DataFrame
            initial_capital: 初始资金

        Returns:
            dict: {strategy_name: BacktestResult}
        """
        results = {}
        for strategy in strategies:
            name = strategy.get_name()
            logger.info("对比回测 - 策略: %s", name)
            results[name] = self.run(strategy, data, initial_capital)
        return results

    def _merge_data_signals(self, data, signals):
        """合并行情数据与交易信号。

        Args:
            data: 标准OHLCV DataFrame
            signals: 信号DataFrame（列：date, signal, position）

        Returns:
            合并后的DataFrame，按日期升序排列
        """
        # 确保日期列类型一致
        data_copy = data.copy()
        signals_copy = signals.copy()
        data_copy["date"] = pd.to_datetime(data_copy["date"])
        signals_copy["date"] = pd.to_datetime(signals_copy["date"])

        merged = data_copy.merge(
            signals_copy[["date", "signal"]], on="date", how="inner"
        )
        merged = merged.sort_values("date").reset_index(drop=True)
        return merged

    def _simulate(self, merged, initial_capital):
        """逐日模拟交易过程。

        Args:
            merged: 合并了信号和行情的DataFrame
            initial_capital: 初始资金

        Returns:
            tuple: (trades, equity_curve, positions)
        """
        cash = initial_capital
        shares = 0
        holding = False  # 是否持仓

        trade_records = []
        equity_records = []
        position_records = []

        for _, row in merged.iterrows():
            date = row["date"]
            open_price = row["open"]
            signal = int(row["signal"])

            # 执行交易
            if signal == 1 and not holding:
                # 买入：以开盘价*(1+slippage)买入，扣除佣金
                buy_price = open_price * (1 + self.slippage)
                # 用全部可用资金买入，取整到100股
                max_shares = int(cash / (buy_price * (1 + self.commission_rate))
                                 // 100 * 100)
                if max_shares > 0:
                    commission = max_shares * buy_price * self.commission_rate
                    cost = max_shares * buy_price + commission
                    cash -= cost
                    shares = max_shares
                    holding = True
                    trade_records.append({
                        "date": date,
                        "direction": "buy",
                        "price": round(buy_price, 4),
                        "quantity": shares,
                        "commission": round(commission, 2),
                    })
                    logger.debug("买入: 日期=%s, 价格=%.4f, 数量=%d",
                                 date, buy_price, shares)

            elif signal == -1 and holding:
                # 卖出：以开盘价*(1-slippage)卖出，扣除佣金和印花税
                sell_price = open_price * (1 - self.slippage)
                commission = shares * sell_price * self.commission_rate
                stamp_tax = shares * sell_price * self.stamp_tax_rate
                revenue = shares * sell_price - commission - stamp_tax
                cash += revenue
                trade_records.append({
                    "date": date,
                    "direction": "sell",
                    "price": round(sell_price, 4),
                    "quantity": shares,
                    "commission": round(commission + stamp_tax, 2),
                })
                logger.debug("卖出: 日期=%s, 价格=%.4f, 数量=%d",
                             date, sell_price, shares)
                shares = 0
                holding = False

            # 记录每日权益和持仓
            market_value = shares * row["close"]
            total_equity = cash + market_value

            equity_records.append({
                "date": date,
                "cash": round(cash, 2),
                "market_value": round(market_value, 2),
                "total_equity": round(total_equity, 2),
            })

            position_records.append({
                "date": date,
                "shares": shares,
                "holding": holding,
                "market_value": round(market_value, 2),
            })

        trades = pd.DataFrame(trade_records)
        equity_curve = pd.DataFrame(equity_records)
        positions = pd.DataFrame(position_records)

        return trades, equity_curve, positions

    def _calculate_performance(self, equity_curve, trades, initial_capital):
        """计算绩效评估指标。

        Args:
            equity_curve: 每日净值曲线DataFrame
            trades: 交易记录DataFrame
            initial_capital: 初始资金

        Returns:
            dict: 绩效指标字典
        """
        if equity_curve.empty:
            return self._empty_performance()

        # 总收益率
        final_equity = equity_curve["total_equity"].iloc[-1]
        total_return = (final_equity - initial_capital) / initial_capital

        # 年化收益率
        trading_days = len(equity_curve)
        if trading_days > 0:
            annualized_return = (
                (1 + total_return) ** (252 / trading_days) - 1
            )
        else:
            annualized_return = 0.0

        # 日收益率序列
        daily_returns = equity_curve["total_equity"].pct_change().dropna()

        # 年化波动率
        if len(daily_returns) > 1:
            annualized_volatility = daily_returns.std() * np.sqrt(252)
        else:
            annualized_volatility = 0.0

        # 夏普比率
        if annualized_volatility > 0:
            sharpe_ratio = (
                (annualized_return - RISK_FREE_RATE) / annualized_volatility
            )
        else:
            sharpe_ratio = 0.0

        # 最大回撤和最大回撤持续天数
        max_drawdown, max_drawdown_duration = self._calculate_drawdown(
            equity_curve["total_equity"]
        )

        # 交易统计
        trade_count = len(trades) // 2  # 买卖各算一次，配对为一次完整交易
        win_rate, profit_loss_ratio = self._calculate_trade_stats(trades)

        # Calmar比率
        if max_drawdown != 0:
            calmar_ratio = annualized_return / abs(max_drawdown)
        else:
            calmar_ratio = 0.0

        performance = {
            "total_return": round(total_return, 6),
            "annualized_return": round(annualized_return, 6),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "max_drawdown": round(max_drawdown, 6),
            "max_drawdown_duration": max_drawdown_duration,
            "win_rate": round(win_rate, 4),
            "profit_loss_ratio": round(profit_loss_ratio, 4),
            "trade_count": trade_count,
            "calmar_ratio": round(calmar_ratio, 4),
        }

        return performance

    @staticmethod
    def _calculate_drawdown(equity_series):
        """计算最大回撤和最大回撤持续天数。

        Args:
            equity_series: 权益序列（pd.Series）

        Returns:
            tuple: (最大回撤, 最大回撤持续天数)
        """
        # 计算累计最高点
        cummax = equity_series.cummax()
        # 回撤序列
        drawdown = (equity_series - cummax) / cummax

        max_drawdown = drawdown.min()

        # 计算最大回撤持续天数
        max_duration = 0
        current_duration = 0
        for dd in drawdown:
            if dd < 0:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0

        return max_drawdown, max_duration

    @staticmethod
    def _calculate_trade_stats(trades):
        """计算交易胜率和盈亏比。

        将买卖配对为完整交易，统计盈利和亏损交易。

        Args:
            trades: 交易记录DataFrame

        Returns:
            tuple: (胜率, 盈亏比)
        """
        if trades.empty or len(trades) < 2:
            return 0.0, 0.0

        # 配对买卖交易，计算每笔交易的盈亏
        profits = []
        buy_price = None
        buy_quantity = None

        for _, trade in trades.iterrows():
            if trade["direction"] == "buy":
                buy_price = trade["price"]
                buy_quantity = trade["quantity"]
            elif trade["direction"] == "sell" and buy_price is not None:
                profit = (trade["price"] - buy_price) * trade["quantity"]
                profits.append(profit)
                buy_price = None
                buy_quantity = None

        if not profits:
            return 0.0, 0.0

        # 胜率
        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]
        win_rate = len(winning) / len(profits) if profits else 0.0

        # 盈亏比
        avg_profit = np.mean(winning) if winning else 0.0
        avg_loss = abs(np.mean(losing)) if losing else 0.0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        return win_rate, profit_loss_ratio

    @staticmethod
    def _empty_performance():
        """返回空绩效指标字典。"""
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "win_rate": 0.0,
            "profit_loss_ratio": 0.0,
            "trade_count": 0,
            "calmar_ratio": 0.0,
        }

    @staticmethod
    def _build_empty_result(strategy_name, data, initial_capital):
        """构建空回测结果（信号为空时使用）。

        Args:
            strategy_name: 策略名称
            data: 原始行情数据
            initial_capital: 初始资金

        Returns:
            BacktestResult: 空结果对象
        """
        # 构建无交易的净值曲线
        if not data.empty:
            equity_records = []
            for _, row in data.iterrows():
                equity_records.append({
                    "date": row["date"],
                    "cash": initial_capital,
                    "market_value": 0.0,
                    "total_equity": initial_capital,
                })
            equity_curve = pd.DataFrame(equity_records)
            position_records = []
            for _, row in data.iterrows():
                position_records.append({
                    "date": row["date"],
                    "shares": 0,
                    "holding": False,
                    "market_value": 0.0,
                })
            positions = pd.DataFrame(position_records)
        else:
            equity_curve = pd.DataFrame(
                columns=["date", "cash", "market_value", "total_equity"]
            )
            positions = pd.DataFrame(
                columns=["date", "shares", "holding", "market_value"]
            )

        return BacktestResult(
            strategy_name=strategy_name,
            performance=BacktestEngine._empty_performance(),
            trades=pd.DataFrame(
                columns=["date", "direction", "price", "quantity", "commission"]
            ),
            equity_curve=equity_curve,
            positions=positions,
        )
