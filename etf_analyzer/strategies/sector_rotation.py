# -*- coding: utf-8 -*-
"""
行业轮动策略模块

基于动量得分的行业轮动策略，支持多ETF排名轮动和单ETF动量计算。
核心逻辑：按动量得分对行业ETF排名，定期调仓持有排名靠前的行业。
"""

import pandas as pd

from etf_analyzer.strategies.base import BaseStrategy
from etf_analyzer.strategies import register_strategy
from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("strategies.sector_rotation")


@register_strategy("sector_rotation")
class SectorRotationStrategy(BaseStrategy):
    """行业轮动策略

    根据动量得分对多只行业ETF进行排名，定期调仓持有排名靠前的行业ETF。

    参数:
        momentum_period: 动量计算周期（交易日），默认20
        top_n: 持仓数量，买入排名前N的行业，默认3
        rebalance_freq: 调仓频率，"monthly"或"weekly"，默认"monthly"
        drop_threshold: 排名跌出前M名时卖出，默认等于top_n
    """

    def __init__(
        self,
        momentum_period: int = 20,
        top_n: int = 3,
        rebalance_freq: str = "monthly",
        drop_threshold: int = None,
    ):
        """初始化行业轮动策略。

        Args:
            momentum_period: 动量计算周期（交易日），必须大于0
            top_n: 持仓数量，必须大于0
            rebalance_freq: 调仓频率，"monthly"或"weekly"
            drop_threshold: 排名跌出前M名时卖出，必须大于等于top_n，
                            为None时默认等于top_n
        """
        if drop_threshold is None:
            drop_threshold = top_n

        params = {
            "momentum_period": momentum_period,
            "top_n": top_n,
            "rebalance_freq": rebalance_freq,
            "drop_threshold": drop_threshold,
        }

        # 参数验证
        if momentum_period <= 0:
            raise ValueError(f"momentum_period 必须大于0，当前值: {momentum_period}")
        if top_n <= 0:
            raise ValueError(f"top_n 必须大于0，当前值: {top_n}")
        if drop_threshold < top_n:
            raise ValueError(
                f"drop_threshold 必须大于等于top_n，"
                f"当前值: drop_threshold={drop_threshold}, top_n={top_n}"
            )
        if rebalance_freq not in ("monthly", "weekly"):
            raise ValueError(
                f"rebalance_freq 必须为 'monthly' 或 'weekly'，当前值: {rebalance_freq}"
            )

        super().__init__(**params)
        logger.info(
            "行业轮动策略初始化: momentum_period=%d, top_n=%d, "
            "rebalance_freq=%s, drop_threshold=%d",
            momentum_period, top_n, rebalance_freq, drop_threshold,
        )

    def _validate_parameters(self, params: dict) -> bool:
        """验证策略参数合法性。"""
        momentum_period = params.get("momentum_period")
        top_n = params.get("top_n")
        rebalance_freq = params.get("rebalance_freq")
        drop_threshold = params.get("drop_threshold")

        if momentum_period is not None and momentum_period <= 0:
            logger.warning("参数验证失败: momentum_period=%d", momentum_period)
            return False
        if top_n is not None and top_n <= 0:
            logger.warning("参数验证失败: top_n=%d", top_n)
            return False
        if rebalance_freq is not None and rebalance_freq not in ("monthly", "weekly"):
            logger.warning("参数验证失败: rebalance_freq=%s", rebalance_freq)
            return False
        if drop_threshold is not None:
            effective_top_n = top_n if top_n is not None else self._params.get("top_n", 3)
            if drop_threshold < effective_top_n:
                logger.warning(
                    "参数验证失败: drop_threshold=%d < top_n=%d",
                    drop_threshold, effective_top_n,
                )
                return False
        return True

    def get_name(self) -> str:
        """返回策略名称。"""
        return "sector_rotation"

    def get_description(self) -> str:
        """返回策略描述。"""
        return (
            f"行业轮动策略：基于{self._params['momentum_period']}日动量得分，"
            f"每{self._params['rebalance_freq']}调仓，"
            f"持有排名前{self._params['top_n']}的行业ETF"
        )

    def _compute_momentum(self, df: pd.DataFrame) -> pd.Series:
        """计算单只ETF的动量得分。

        动量得分 = (当日收盘价 - N日前收盘价) / N日前收盘价

        Args:
            df: 包含 close 列的 DataFrame

        Returns:
            pd.Series: 动量得分序列，前 momentum_period 个值为 NaN
        """
        period = self._params["momentum_period"]
        return (df["close"] - df["close"].shift(period)) / df["close"].shift(period)

    def _get_rebalance_dates(self, dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
        """根据调仓频率确定调仓日期。

        选取每月/每周的第一个交易日作为调仓日。

        Args:
            dates: 所有交易日的 DatetimeIndex

        Returns:
            pd.DatetimeIndex: 调仓日期集合
        """
        freq = self._params["rebalance_freq"]
        if freq == "monthly":
            # 按年月分组，取每组第一个日期
            groups = dates.to_series().groupby(dates.to_period("M")).first()
            return pd.DatetimeIndex(groups.values)
        else:
            # 按年周分组，取每组第一个日期
            groups = dates.to_series().groupby(dates.to_period("W")).first()
            return pd.DatetimeIndex(groups.values)

    def generate_signals(self, data) -> pd.DataFrame:
        """生成行业轮动交易信号。

        支持两种输入模式：
            - 单ETF模式：data 为 DataFrame，计算该ETF的动量得分和信号
            - 多ETF模式：data 为字典 {symbol: DataFrame}，计算所有ETF动量排名并生成信号

        Args:
            data: 标准OHLCV DataFrame 或 {symbol: DataFrame} 字典

        Returns:
            pd.DataFrame: 信号DataFrame
                单ETF模式列：date, signal, position
                多ETF模式列：date, symbol, signal, position
        """
        if isinstance(data, dict):
            return self._generate_multi_signals(data)
        else:
            return self._generate_single_signals(data)

    def _generate_single_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """单ETF模式：计算该ETF的动量得分和信号。

        动量得分 > 0 → signal=1, position=1.0
        动量得分 <= 0 → signal=-1, position=0.0
        动量得分为 NaN → signal=0, position=0.0

        Args:
            data: 标准OHLCV DataFrame

        Returns:
            pd.DataFrame: 包含 date, signal, position 列的信号DataFrame
        """
        df = data.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # 计算动量得分
        df["momentum"] = self._compute_momentum(df)

        # 生成信号
        df["signal"] = 0
        df["position"] = 0.0

        # 动量得分为正 → 买入
        positive_mask = df["momentum"] > 0
        df.loc[positive_mask, "signal"] = 1
        df.loc[positive_mask, "position"] = 1.0

        # 动量得分为负或为零 → 卖出
        negative_mask = df["momentum"] <= 0
        df.loc[negative_mask & df["momentum"].notna(), "signal"] = -1
        df.loc[negative_mask & df["momentum"].notna(), "position"] = 0.0

        # 动量得分为 NaN（数据不足）→ 不操作
        nan_mask = df["momentum"].isna()
        df.loc[nan_mask, "signal"] = 0
        df.loc[nan_mask, "position"] = 0.0

        logger.info("单ETF模式信号生成完成，共 %d 条记录", len(df))
        return df[["date", "signal", "position"]]

    def _generate_multi_signals(self, data: dict) -> pd.DataFrame:
        """多ETF模式：计算所有ETF动量排名并生成信号。

        按调仓频率计算排名：
            - 排名前top_n → signal=1, position=1.0/top_n
            - 排名跌出drop_threshold → signal=-1, position=0.0
            - 其他 → signal=0, position=0.0

        Args:
            data: {symbol: DataFrame} 字典，每个DataFrame为标准OHLCV格式

        Returns:
            pd.DataFrame: 包含 date, symbol, signal, position 列的信号DataFrame
        """
        top_n = self._params["top_n"]
        drop_threshold = self._params["drop_threshold"]

        # 计算每只ETF的动量得分
        momentum_dict = {}
        for symbol, df in data.items():
            df_copy = df.copy()
            df_copy["date"] = pd.to_datetime(df_copy["date"])
            df_copy = df_copy.sort_values("date").reset_index(drop=True)
            df_copy["momentum"] = self._compute_momentum(df_copy)
            momentum_dict[symbol] = df_copy[["date", "momentum"]].copy()

        # 合并所有ETF的动量得分，构建宽表
        merged = None
        for symbol, df in momentum_dict.items():
            temp = df.rename(columns={"momentum": symbol})
            if merged is None:
                merged = temp
            else:
                merged = merged.merge(temp, on="date", how="outer")

        merged = merged.sort_values("date").reset_index(drop=True)
        all_dates = pd.DatetimeIndex(merged["date"])
        rebalance_dates = self._get_rebalance_dates(all_dates)
        rebalance_set = set(rebalance_dates)

        # 初始化信号记录
        signals_records = []

        # 跟踪当前持仓状态 {symbol: bool}
        holding = {symbol: False for symbol in momentum_dict.keys()}
        # 记录上一次调仓的排名
        last_rank = None

        for idx, row in merged.iterrows():
            current_date = row["date"]
            is_rebalance = current_date in rebalance_set

            if is_rebalance:
                # 调仓日：计算动量排名
                momentum_scores = {}
                for symbol in momentum_dict.keys():
                    score = row.get(symbol)
                    if pd.notna(score):
                        momentum_scores[symbol] = score

                # 按动量得分降序排名
                sorted_symbols = sorted(
                    momentum_scores.keys(),
                    key=lambda s: momentum_scores[s],
                    reverse=True,
                )
                last_rank = {s: rank + 1 for rank, s in enumerate(sorted_symbols)}

                # 生成调仓信号
                for symbol in momentum_dict.keys():
                    rank = last_rank.get(symbol)
                    if rank is None:
                        # 无动量数据，不操作
                        signals_records.append({
                            "date": current_date,
                            "symbol": symbol,
                            "signal": 0,
                            "position": 0.0,
                        })
                        holding[symbol] = False
                    elif rank <= top_n:
                        # 排名前top_n → 买入
                        signals_records.append({
                            "date": current_date,
                            "symbol": symbol,
                            "signal": 1,
                            "position": round(1.0 / top_n, 4),
                        })
                        holding[symbol] = True
                    elif rank > drop_threshold:
                        # 排名跌出drop_threshold → 卖出
                        signals_records.append({
                            "date": current_date,
                            "symbol": symbol,
                            "signal": -1,
                            "position": 0.0,
                        })
                        holding[symbol] = False
                    else:
                        # 中间排名 → 不持有
                        signals_records.append({
                            "date": current_date,
                            "symbol": symbol,
                            "signal": 0,
                            "position": 0.0,
                        })
                        holding[symbol] = False
            else:
                # 非调仓日：维持当前持仓状态，信号为0
                for symbol in momentum_dict.keys():
                    pos = round(1.0 / top_n, 4) if holding[symbol] else 0.0
                    signals_records.append({
                        "date": current_date,
                        "symbol": symbol,
                        "signal": 0,
                        "position": pos,
                    })

        result = pd.DataFrame(signals_records)
        logger.info(
            "多ETF模式信号生成完成，共 %d 只ETF，%d 条记录",
            len(momentum_dict), len(result),
        )
        return result[["date", "symbol", "signal", "position"]]
