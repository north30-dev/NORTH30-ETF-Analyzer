# -*- coding: utf-8 -*-
"""
信号生成模块

提供实时信号计算、仓位建议和策略执行报告功能。
SignalGenerator 基于 BaseStrategy 实例生成的信号数据，
为用户提供可操作的交易建议和风险提示。
"""

from datetime import datetime

import pandas as pd

from etf_analyzer.utils.logger import setup_logger


class SignalGenerator:
    """信号生成器，提供实时信号计算、仓位建议和策略执行报告。"""

    def __init__(self):
        self.logger = setup_logger("signal_generator")

    def generate_signal(self, strategy, data) -> dict:
        """计算当前信号和仓位建议。

        Args:
            strategy: BaseStrategy 实例
            data: 标准OHLCV DataFrame

        Returns:
            dict: {
                "signal": int,           # 1=买入, -1=卖出, 0=持有
                "position": float,       # 建议仓位 0.0~1.0
                "signal_strength": float, # 信号强度 0.0~1.0
                "timestamp": str,        # 信号时间
                "strategy_name": str,    # 策略名称
            }
        """
        self.logger.info("开始生成信号，策略: %s", strategy.get_name())

        # 调用策略生成信号
        signals_df = strategy.generate_signals(data)

        if signals_df.empty:
            self.logger.warning("策略 %s 未生成任何信号", strategy.get_name())
            return {
                "signal": 0,
                "position": 0.0,
                "signal_strength": 0.0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "strategy_name": strategy.get_name(),
            }

        # 取最后一行作为当前信号
        last_row = signals_df.iloc[-1]
        signal = int(last_row["signal"])
        position = float(last_row["position"])

        # 计算信号强度：基于近期信号一致性
        signal_strength = self._calculate_signal_strength(signals_df)

        # 获取时间戳
        timestamp = self._extract_timestamp(last_row)

        result = {
            "signal": signal,
            "position": position,
            "signal_strength": round(signal_strength, 4),
            "timestamp": timestamp,
            "strategy_name": strategy.get_name(),
        }

        self.logger.info(
            "信号生成完成 - 策略: %s, 信号: %d, 仓位: %.2f, 强度: %.4f",
            strategy.get_name(), signal, position, signal_strength,
        )
        return result

    def generate_position_advice(self, signal, position, current_position=0.0) -> dict:
        """根据信号和仓位生成仓位建议。

        Args:
            signal: 信号值
            position: 策略建议仓位
            current_position: 当前持仓仓位

        Returns:
            dict: {
                "action": str,        # "buy"/"sell"/"hold"
                "target_position": float,  # 目标仓位
                "adjustment": float,       # 需要调整的仓位
                "risk_level": str,         # "low"/"medium"/"high"
            }
        """
        # 根据信号确定目标仓位和操作方向
        if signal == 1:
            # 买入信号：建议仓位0.3~1.0
            target_position = max(0.3, min(1.0, position))
            action = "buy"
        elif signal == -1:
            # 卖出信号：建议减仓至0~0.3
            target_position = min(0.3, max(0.0, position))
            action = "sell"
        else:
            # 持有信号：维持当前仓位
            target_position = current_position
            action = "hold"

        # 计算需要调整的仓位
        adjustment = round(target_position - current_position, 4)

        # 根据仓位调整幅度确定风险等级
        abs_adjustment = abs(adjustment)
        if abs_adjustment < 0.2:
            risk_level = "low"
        elif abs_adjustment <= 0.5:
            risk_level = "medium"
        else:
            risk_level = "high"

        result = {
            "action": action,
            "target_position": round(target_position, 4),
            "adjustment": adjustment,
            "risk_level": risk_level,
        }

        self.logger.info(
            "仓位建议 - 操作: %s, 目标仓位: %.4f, 调整: %.4f, 风险: %s",
            action, target_position, adjustment, risk_level,
        )
        return result

    def generate_report(self, strategy, data, recent_days=30) -> dict:
        """生成策略执行报告。

        Args:
            strategy: BaseStrategy 实例
            data: 标准OHLCV DataFrame
            recent_days: 近期天数，默认30

        Returns:
            dict: {
                "current_signal": dict,        # 当前信号
                "signal_statistics": dict,     # 历史信号统计
                "recent_trades": list,         # 近期交易建议
                "risk_warnings": list,         # 风险提示
                "strategy_info": dict,         # 策略信息
            }
        """
        self.logger.info("开始生成策略执行报告，策略: %s", strategy.get_name())

        # 调用策略生成全量信号
        signals_df = strategy.generate_signals(data)

        # 当前信号
        current_signal = self.generate_signal(strategy, data)

        # 历史信号统计
        signal_statistics = self._calculate_signal_statistics(signals_df)

        # 近期交易建议
        recent_trades = self._extract_recent_trades(signals_df, recent_days)

        # 风险提示
        risk_warnings = self._generate_risk_warnings(
            signals_df, current_signal, recent_days,
        )

        # 策略信息
        strategy_info = {
            "name": strategy.get_name(),
            "description": strategy.get_description(),
            "parameters": strategy.get_parameters(),
        }

        report = {
            "current_signal": current_signal,
            "signal_statistics": signal_statistics,
            "recent_trades": recent_trades,
            "risk_warnings": risk_warnings,
            "strategy_info": strategy_info,
        }

        self.logger.info("策略执行报告生成完成，策略: %s", strategy.get_name())
        return report

    def _calculate_signal_strength(self, signals_df) -> float:
        """计算信号强度，基于近期信号一致性。

        取最近5个信号，计算与当前信号方向一致的比例。

        Args:
            signals_df: 策略生成的信号DataFrame

        Returns:
            float: 信号强度 0.0~1.0
        """
        if len(signals_df) < 2:
            return 0.0

        # 取最近5个信号（至少2个）
        lookback = min(5, len(signals_df))
        recent_signals = signals_df["signal"].iloc[-lookback:].values

        # 当前信号
        current_signal = int(recent_signals[-1])

        if current_signal == 0:
            # 持有信号的强度取决于近期信号的稳定性
            consistency = sum(1 for s in recent_signals if s == 0) / len(recent_signals)
            return consistency

        # 计算与当前信号方向一致的比例
        consistent_count = sum(1 for s in recent_signals if s == current_signal)
        strength = consistent_count / len(recent_signals)
        return strength

    def _extract_timestamp(self, row) -> str:
        """从信号行中提取时间戳。

        Args:
            row: signals_df 的一行

        Returns:
            str: 格式化的时间字符串
        """
        if "date" in row.index:
            date_val = row["date"]
            if isinstance(date_val, pd.Timestamp):
                return date_val.strftime("%Y-%m-%d")
            return str(date_val)
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _calculate_signal_statistics(self, signals_df) -> dict:
        """统计全量信号中买入/卖出/持有次数及占比。

        Args:
            signals_df: 策略生成的信号DataFrame

        Returns:
            dict: 信号统计信息
        """
        if signals_df.empty:
            return {
                "total": 0,
                "buy_count": 0,
                "sell_count": 0,
                "hold_count": 0,
                "buy_ratio": 0.0,
                "sell_ratio": 0.0,
                "hold_ratio": 0.0,
            }

        total = len(signals_df)
        buy_count = int((signals_df["signal"] == 1).sum())
        sell_count = int((signals_df["signal"] == -1).sum())
        hold_count = int((signals_df["signal"] == 0).sum())

        return {
            "total": total,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "buy_ratio": round(buy_count / total, 4) if total > 0 else 0.0,
            "sell_ratio": round(sell_count / total, 4) if total > 0 else 0.0,
            "hold_ratio": round(hold_count / total, 4) if total > 0 else 0.0,
        }

    def _extract_recent_trades(self, signals_df, recent_days) -> list:
        """提取近N天中信号变化的日期和操作建议。

        检测信号发生变化的日期，生成对应的交易建议。

        Args:
            signals_df: 策略生成的信号DataFrame
            recent_days: 近期天数

        Returns:
            list: 近期交易建议列表
        """
        if signals_df.empty or len(signals_df) < 2:
            return []

        # 取近N天的数据
        recent_df = signals_df.tail(recent_days)

        recent_trades = []
        prev_signal = int(recent_df["signal"].iloc[0])

        for idx in range(1, len(recent_df)):
            curr_row = recent_df.iloc[idx]
            curr_signal = int(curr_row["signal"])

            # 信号发生变化时记录交易建议
            if curr_signal != prev_signal:
                action = self._signal_to_action(curr_signal)
                date_str = self._extract_timestamp(curr_row)

                recent_trades.append({
                    "date": date_str,
                    "signal": curr_signal,
                    "action": action,
                    "position": float(curr_row["position"]),
                })

            prev_signal = curr_signal

        return recent_trades

    def _signal_to_action(self, signal) -> str:
        """将信号值转换为操作描述。

        Args:
            signal: 信号值

        Returns:
            str: 操作描述
        """
        if signal == 1:
            return "买入"
        elif signal == -1:
            return "卖出"
        return "持有"

    def _generate_risk_warnings(self, signals_df, current_signal, recent_days) -> list:
        """基于信号频率和仓位集中度生成风险提示。

        Args:
            signals_df: 策略生成的信号DataFrame
            current_signal: 当前信号字典
            recent_days: 近期天数

        Returns:
            list: 风险提示列表
        """
        warnings = []

        if signals_df.empty:
            return warnings

        # 取近N天的数据
        recent_df = signals_df.tail(recent_days)

        # 1. 频繁交易风险：近期信号变化次数过多
        if len(recent_df) >= 2:
            signal_changes = 0
            prev_signal = int(recent_df["signal"].iloc[0])
            for i in range(1, len(recent_df)):
                curr_signal = int(recent_df["signal"].iloc[i])
                if curr_signal != prev_signal:
                    signal_changes += 1
                prev_signal = curr_signal

            # 信号变化频率：平均每几天变化一次
            if signal_changes > 0:
                avg_interval = len(recent_df) / signal_changes
                if avg_interval < 3:
                    warnings.append(
                        f"频繁交易风险：近{recent_days}天内信号变化{signal_changes}次，"
                        f"平均{avg_interval:.1f}天变化一次，建议关注交易成本"
                    )

        # 2. 仓位集中度风险：当前建议仓位过高
        current_position = current_signal.get("position", 0.0)
        if current_position >= 0.8:
            warnings.append(
                f"仓位集中度风险：当前建议仓位为{current_position:.0%}，"
                f"持仓过于集中，建议分散投资"
            )

        # 3. 信号强度不足风险
        signal_strength = current_signal.get("signal_strength", 0.0)
        if signal_strength < 0.4 and current_signal.get("signal", 0) != 0:
            warnings.append(
                f"信号强度不足：当前信号强度为{signal_strength:.2f}，"
                f"信号可靠性较低，建议谨慎操作"
            )

        # 4. 连续亏损风险：近期卖出信号占比过高
        if len(recent_df) >= 5:
            sell_ratio = (recent_df["signal"] == -1).sum() / len(recent_df)
            if sell_ratio > 0.6:
                warnings.append(
                    f"连续卖出风险：近{recent_days}天卖出信号占比"
                    f"{sell_ratio:.0%}，市场可能处于下行趋势"
                )

        return warnings
