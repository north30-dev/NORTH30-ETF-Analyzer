# -*- coding: utf-8 -*-
"""
ETF分析器可视化模块

本模块提供ETF数据的多种可视化功能，包括K线图、净值走势图、
行业分布饼图、成分股权重柱状图、自定义图表和回撤曲线图等，
帮助用户直观地了解ETF的各项指标和分布情况。
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import numpy as np

from etf_analyzer.utils.logger import setup_logger

# 设置全局中文字体和负号显示
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

logger = setup_logger("visualizer")


class ETFVisualizer:
    """ETF数据可视化器，提供K线图、净值走势图、行业分布饼图等多种图表绘制功能。

    该类封装了基于 matplotlib 和 mplfinance 的图表绘制方法，
    支持中文字体显示、图片保存和交互式展示等功能。
    """

    def plot_kline(self, df, symbol="", save_path=None, show=True):
        """绘制ETF K线图（含成交量副图）。

        使用 mplfinance 库绘制专业的K线图，包含蜡烛图和成交量副图。
        输入的 DataFrame 需要包含日期、开盘价、收盘价、最高价、最低价和成交量列，
        方法内部会自动将列名转换为 mplfinance 要求的格式。

        Args:
            df (pd.DataFrame): 包含历史行情数据的 DataFrame，需包含以下列：
                - 日期列（索引或名为'date'/'日期'的列）
                - 开盘价列（名为'open'/'开盘'/'Open'）
                - 收盘价列（名为'close'/'收盘'/'Close'）
                - 最高价列（名为'high'/'最高'/'High'）
                - 最低价列（名为'low'/'最低'/'Low'）
                - 成交量列（名为'volume'/'成交量'/'Volume'）
            symbol (str): ETF代码，用于图表标题显示，默认为空字符串。
            save_path (str, optional): 图片保存路径。如果为 None 则不保存，默认为 None。
            show (bool): 是否调用 plt.show() 显示图表，默认为 True。

        Returns:
            matplotlib.figure.Figure: 生成的图表对象，可用于进一步操作或保存。

        Raises:
            ValueError: 当输入的 DataFrame 为空或缺少必要列时抛出。
        """
        try:
            if df is None or df.empty:
                raise ValueError("输入的 DataFrame 为空，无法绘制K线图")

            logger.info("开始绘制K线图，ETF代码: %s", symbol)

            # 复制数据，避免修改原始 DataFrame
            data = df.copy()

            # 将日期列设为索引（如果还不是索引）
            if not isinstance(data.index, pd.DatetimeIndex):
                date_col = None
                for col_name in ["date", "Date", "日期", "trade_date"]:
                    if col_name in data.columns:
                        date_col = col_name
                        break
                if date_col is not None:
                    data[date_col] = pd.to_datetime(data[date_col])
                    data.set_index(date_col, inplace=True)
                else:
                    # 尝试将索引转换为日期
                    data.index = pd.to_datetime(data.index)

            # 列名映射：将中文/小写列名映射为 mplfinance 要求的格式
            col_mapping = {}
            for col in data.columns:
                col_lower = col.lower()
                if col_lower in ("open", "开盘", "开盘价"):
                    col_mapping[col] = "Open"
                elif col_lower in ("high", "最高", "最高价"):
                    col_mapping[col] = "High"
                elif col_lower in ("low", "最低", "最低价"):
                    col_mapping[col] = "Low"
                elif col_lower in ("close", "收盘", "收盘价"):
                    col_mapping[col] = "Close"
                elif col_lower in ("volume", "成交量", "vol"):
                    col_mapping[col] = "Volume"

            data.rename(columns=col_mapping, inplace=True)

            # 检查必要列是否存在
            required_cols = ["Open", "High", "Low", "Close"]
            missing_cols = [c for c in required_cols if c not in data.columns]
            if missing_cols:
                raise ValueError(
                    f"DataFrame 缺少必要列: {missing_cols}，"
                    f"当前列名: {list(data.columns)}"
                )

            # 只保留 mplfinance 需要的列
            keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"]
                         if c in data.columns]
            data = data[keep_cols]

            # 确保数据类型为浮点数
            for col in data.columns:
                data[col] = pd.to_numeric(data[col], errors="coerce")

            # 去除含 NaN 的行
            data.dropna(inplace=True)

            if data.empty:
                raise ValueError("数据清洗后为空，无法绘制K线图")

            # 设置 mplfinance 样式
            mc = mpf.make_marketcolors(
                up="red",
                down="green",
                edge="inherit",
                wick="inherit",
                volume={"up": "red", "down": "green"},
            )
            style = mpf.make_mpf_style(
                marketcolors=mc,
                figcolor="white",
                gridstyle="--",
                gridaxis="both",
            )

            # 绘制K线图
            kwargs = {
                "type": "candle",
                "style": style,
                "volume": "Volume" in data.columns,
                "title": f"{symbol} K线图" if symbol else "K线图",
                "returnfig": True,
                "figsize": (12, 8),
                "datetime_format": "%Y-%m-%d",
            }
            fig, axes = mpf.plot(data, **kwargs)

            # 保存图片
            if save_path:
                fig.savefig(save_path, dpi=150, bbox_inches="tight")
                logger.info("K线图已保存至: %s", save_path)

            # 显示图表
            if show:
                plt.show()

            logger.info("K线图绘制完成，ETF代码: %s", symbol)
            return fig

        except ValueError:
            raise
        except Exception as e:
            logger.error("绘制K线图时发生错误: %s", e)
            raise

    def plot_nav_trend(self, nav_data, benchmark_data=None, symbol="",
                       benchmark_name="", save_path=None, show=True):
        """绘制ETF净值走势图，可叠加基准对比曲线。

        绘制ETF净值随时间变化的走势曲线，如果提供了基准数据，
        则在同一图中绘制基准对比曲线，使用不同颜色和图例区分。

        Args:
            nav_data (pd.DataFrame): ETF净值数据，需包含日期列和收盘价列。
                日期列支持名称: 'date'/'Date'/'日期'/'trade_date'。
                收盘价列支持名称: 'close'/'Close'/'收盘'/'收盘价'。
            benchmark_data (pd.DataFrame, optional): 基准数据，格式与 nav_data 相同。
                默认为 None，表示不绘制基准曲线。
            symbol (str): ETF代码，用于图表标题显示，默认为空字符串。
            benchmark_name (str): 基准名称，用于图例显示，默认为空字符串。
            save_path (str, optional): 图片保存路径。如果为 None 则不保存，默认为 None。
            show (bool): 是否调用 plt.show() 显示图表，默认为 True。

        Returns:
            matplotlib.figure.Figure: 生成的图表对象。

        Raises:
            ValueError: 当输入的 DataFrame 为空或缺少必要列时抛出。
        """
        try:
            if nav_data is None or nav_data.empty:
                raise ValueError("输入的净值 DataFrame 为空，无法绘制净值走势图")

            logger.info("开始绘制净值走势图，ETF代码: %s", symbol)

            fig, ax = plt.subplots(figsize=(12, 6))

            # 提取日期列和收盘价列
            nav_dates = self._extract_column(nav_data, ["date", "Date", "日期", "trade_date"])
            nav_close = self._extract_column(nav_data, ["close", "Close", "收盘", "收盘价"])

            if nav_dates is None or nav_close is None:
                raise ValueError(
                    "净值数据缺少日期列或收盘价列，"
                    f"当前列名: {list(nav_data.columns)}"
                )

            nav_dates = pd.to_datetime(nav_dates)
            ax.plot(nav_dates, nav_close, label=symbol or "ETF净值", color="blue", linewidth=1.5)

            # 绘制基准曲线
            if benchmark_data is not None and not benchmark_data.empty:
                bm_dates = self._extract_column(benchmark_data, ["date", "Date", "日期", "trade_date"])
                bm_close = self._extract_column(benchmark_data, ["close", "Close", "收盘", "收盘价"])

                if bm_dates is not None and bm_close is not None:
                    bm_dates = pd.to_datetime(bm_dates)
                    bm_label = benchmark_name or "基准"
                    ax.plot(bm_dates, bm_close, label=bm_label, color="orange",
                            linewidth=1.2, linestyle="--")

            title = f"{symbol} 净值走势图" if symbol else "净值走势图"
            ax.set_title(title, fontsize=14)
            ax.set_xlabel("日期", fontsize=12)
            ax.set_ylabel("净值", fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(True, linestyle="--", alpha=0.7)

            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=150, bbox_inches="tight")
                logger.info("净值走势图已保存至: %s", save_path)

            if show:
                plt.show()

            logger.info("净值走势图绘制完成，ETF代码: %s", symbol)
            return fig

        except ValueError:
            raise
        except Exception as e:
            logger.error("绘制净值走势图时发生错误: %s", e)
            raise

    def plot_industry_pie(self, industry_data, symbol="", save_path=None, show=True):
        """绘制ETF行业持仓分布饼图。

        根据行业持仓占比数据绘制饼图，对于占比小于3%的行业，
        自动合并为"其他"类别，避免饼图过于碎片化。

        Args:
            industry_data (pd.DataFrame): 行业分布数据，需包含行业名称列和持仓占比列。
                行业名称列支持名称: 'industry'/'行业'/'行业名称'/'行业分类'。
                持仓占比列支持名称: 'weight'/'占比'/'持仓占比'/'比例'/'holding'。
            symbol (str): ETF代码，用于图表标题显示，默认为空字符串。
            save_path (str, optional): 图片保存路径。如果为 None 则不保存，默认为 None。
            show (bool): 是否调用 plt.show() 显示图表，默认为 True。

        Returns:
            matplotlib.figure.Figure: 生成的图表对象。

        Raises:
            ValueError: 当输入的 DataFrame 为空或缺少必要列时抛出。
        """
        try:
            if industry_data is None or industry_data.empty:
                raise ValueError("输入的行业分布 DataFrame 为空，无法绘制饼图")

            logger.info("开始绘制行业分布饼图，ETF代码: %s", symbol)

            # 提取行业名称列和持仓占比列
            industry_col = self._extract_column_name(
                industry_data,
                ["industry", "行业", "行业名称", "行业分类"]
            )
            weight_col = self._extract_column_name(
                industry_data,
                ["weight", "占比", "持仓占比", "比例", "holding"]
            )

            if industry_col is None or weight_col is None:
                raise ValueError(
                    "行业数据缺少行业名称列或持仓占比列，"
                    f"当前列名: {list(industry_data.columns)}"
                )

            # 复制数据
            data = industry_data[[industry_col, weight_col]].copy()
            data[weight_col] = pd.to_numeric(data[weight_col], errors="coerce")
            data.dropna(inplace=True)

            if data.empty:
                raise ValueError("行业数据清洗后为空，无法绘制饼图")

            # 合并占比小于3%的行业为"其他"
            threshold = 3.0
            small_mask = data[weight_col] < threshold
            if small_mask.any():
                other_sum = data.loc[small_mask, weight_col].sum()
                data = data.loc[~small_mask].copy()
                if other_sum > 0:
                    other_row = pd.DataFrame({industry_col: ["其他"], weight_col: [other_sum]})
                    data = pd.concat([data, other_row], ignore_index=True)

            labels = data[industry_col].tolist()
            sizes = data[weight_col].tolist()

            fig, ax = plt.subplots(figsize=(10, 8))
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct="%1.1f%%",
                startangle=90,
                pctdistance=0.85,
            )

            # 设置百分比文字大小
            for autotext in autotexts:
                autotext.set_fontsize(9)

            # 添加图例
            ax.legend(
                wedges,
                [f"{l} ({s:.1f}%)" for l, s in zip(labels, sizes)],
                title="行业",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                fontsize=9,
            )

            title = f"{symbol} 行业分布" if symbol else "行业分布"
            ax.set_title(title, fontsize=14)

            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=150, bbox_inches="tight")
                logger.info("行业分布饼图已保存至: %s", save_path)

            if show:
                plt.show()

            logger.info("行业分布饼图绘制完成，ETF代码: %s", symbol)
            return fig

        except ValueError:
            raise
        except Exception as e:
            logger.error("绘制行业分布饼图时发生错误: %s", e)
            raise

    def plot_holdings_bar(self, holdings_data, symbol="", save_path=None, show=True):
        """绘制ETF前十大成分股权重水平柱状图。

        以水平柱状图的形式展示ETF前十大成分股的持仓占比，
        并在柱状图上标注具体的占比数值，便于直观比较各成分股的权重。

        Args:
            holdings_data (pd.DataFrame): 成分股数据，需包含股票名称列和持仓占比列。
                股票名称列支持名称: 'name'/'名称'/'股票名称'/'股票'/'stock'。
                持仓占比列支持名称: 'weight'/'占比'/'持仓占比'/'比例'/'holding'。
            symbol (str): ETF代码，用于图表标题显示，默认为空字符串。
            save_path (str, optional): 图片保存路径。如果为 None 则不保存，默认为 None。
            show (bool): 是否调用 plt.show() 显示图表，默认为 True。

        Returns:
            matplotlib.figure.Figure: 生成的图表对象。

        Raises:
            ValueError: 当输入的 DataFrame 为空或缺少必要列时抛出。
        """
        try:
            if holdings_data is None or holdings_data.empty:
                raise ValueError("输入的成分股 DataFrame 为空，无法绘制柱状图")

            logger.info("开始绘制成分股权重柱状图，ETF代码: %s", symbol)

            # 提取股票名称列和持仓占比列
            name_col = self._extract_column_name(
                holdings_data,
                ["name", "名称", "股票名称", "股票", "stock"]
            )
            weight_col = self._extract_column_name(
                holdings_data,
                ["weight", "占比", "持仓占比", "比例", "holding"]
            )

            if name_col is None or weight_col is None:
                raise ValueError(
                    "成分股数据缺少股票名称列或持仓占比列，"
                    f"当前列名: {list(holdings_data.columns)}"
                )

            # 复制数据并取前十大
            data = holdings_data[[name_col, weight_col]].copy()
            data[weight_col] = pd.to_numeric(data[weight_col], errors="coerce")
            data.dropna(inplace=True)
            data = data.head(10)

            if data.empty:
                raise ValueError("成分股数据清洗后为空，无法绘制柱状图")

            names = data[name_col].tolist()
            weights = data[weight_col].tolist()

            # 反转顺序，使最大权重在顶部
            names = names[::-1]
            weights = weights[::-1]

            fig, ax = plt.subplots(figsize=(10, 6))
            y_pos = range(len(names))
            bars = ax.barh(y_pos, weights, color="steelblue", height=0.6)

            # 在柱状图上标注具体占比数值
            for bar, w in zip(bars, weights):
                ax.text(
                    bar.get_width() + max(weights) * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{w:.2f}%",
                    va="center",
                    fontsize=9,
                )

            ax.set_yticks(y_pos)
            ax.set_yticklabels(names, fontsize=10)
            ax.set_xlabel("持仓占比 (%)", fontsize=12)

            title = f"{symbol} 前十大权重股" if symbol else "前十大权重股"
            ax.set_title(title, fontsize=14)
            ax.grid(axis="x", linestyle="--", alpha=0.7)

            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=150, bbox_inches="tight")
                logger.info("成分股权重柱状图已保存至: %s", save_path)

            if show:
                plt.show()

            logger.info("成分股权重柱状图绘制完成，ETF代码: %s", symbol)
            return fig

        except ValueError:
            raise
        except Exception as e:
            logger.error("绘制成分股权重柱状图时发生错误: %s", e)
            raise

    def plot_custom(self, df, x_col, y_cols, title="", xlabel="", ylabel="",
                    save_path=None, show=True):
        """绘制自定义图表，支持多条Y轴数据在同一图中展示。

        通用的绘图方法，用户可以自由指定X轴列名和Y轴列名列表，
        支持在同一图中绘制多条曲线，适用于各种自定义数据可视化需求。

        Args:
            df (pd.DataFrame): 数据源 DataFrame。
            x_col (str): X轴对应的列名。
            y_cols (list[str]): Y轴对应的列名列表，每个列名绘制一条曲线。
            title (str): 图表标题，默认为空字符串。
            xlabel (str): X轴标签，默认为空字符串。
            ylabel (str): Y轴标签，默认为空字符串。
            save_path (str, optional): 图片保存路径。如果为 None 则不保存，默认为 None。
            show (bool): 是否调用 plt.show() 显示图表，默认为 True。

        Returns:
            matplotlib.figure.Figure: 生成的图表对象。

        Raises:
            ValueError: 当输入的 DataFrame 为空、指定的列不存在或 y_cols 为空时抛出。
        """
        try:
            if df is None or df.empty:
                raise ValueError("输入的 DataFrame 为空，无法绘制自定义图表")

            if not y_cols:
                raise ValueError("y_cols 不能为空，至少需要指定一个Y轴列名")

            logger.info("开始绘制自定义图表，X轴: %s, Y轴: %s", x_col, y_cols)

            # 检查列是否存在
            all_cols = [x_col] + y_cols
            missing_cols = [c for c in all_cols if c not in df.columns]
            if missing_cols:
                raise ValueError(
                    f"DataFrame 中不存在以下列: {missing_cols}，"
                    f"当前列名: {list(df.columns)}"
                )

            fig, ax = plt.subplots(figsize=(12, 6))

            x_data = df[x_col]

            # 尝试将X轴数据转为日期
            try:
                x_data = pd.to_datetime(x_data)
            except (ValueError, TypeError):
                pass

            # 定义多条曲线的颜色
            colors = ["blue", "orange", "green", "red", "purple",
                      "brown", "pink", "gray", "olive", "cyan"]

            for i, y_col in enumerate(y_cols):
                color = colors[i % len(colors)]
                ax.plot(x_data, df[y_col], label=y_col, color=color, linewidth=1.2)

            if title:
                ax.set_title(title, fontsize=14)
            if xlabel:
                ax.set_xlabel(xlabel, fontsize=12)
            if ylabel:
                ax.set_ylabel(ylabel, fontsize=12)

            ax.legend(fontsize=10)
            ax.grid(True, linestyle="--", alpha=0.7)

            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=150, bbox_inches="tight")
                logger.info("自定义图表已保存至: %s", save_path)

            if show:
                plt.show()

            logger.info("自定义图表绘制完成")
            return fig

        except ValueError:
            raise
        except Exception as e:
            logger.error("绘制自定义图表时发生错误: %s", e)
            raise

    def plot_drawdown(self, df, symbol="", save_path=None, show=True):
        """计算并绘制ETF回撤曲线图。

        根据收盘价数据计算每个时间点的回撤幅度，并绘制回撤曲线图，
        直观展示ETF的历史最大回撤及回撤变化趋势。

        回撤计算公式：drawdown = (price - cummax) / cummax

        Args:
            df (pd.DataFrame): 包含日期和收盘价列的数据。
                日期列支持名称: 'date'/'Date'/'日期'/'trade_date'。
                收盘价列支持名称: 'close'/'Close'/'收盘'/'收盘价'。
            symbol (str): ETF代码，用于图表标题显示，默认为空字符串。
            save_path (str, optional): 图片保存路径。如果为 None 则不保存，默认为 None。
            show (bool): 是否调用 plt.show() 显示图表，默认为 True。

        Returns:
            matplotlib.figure.Figure: 生成的图表对象。

        Raises:
            ValueError: 当输入的 DataFrame 为空或缺少必要列时抛出。
        """
        try:
            if df is None or df.empty:
                raise ValueError("输入的 DataFrame 为空，无法绘制回撤曲线图")

            logger.info("开始绘制回撤曲线图，ETF代码: %s", symbol)

            # 提取日期列和收盘价列
            dates = self._extract_column(df, ["date", "Date", "日期", "trade_date"])
            close = self._extract_column(df, ["close", "Close", "收盘", "收盘价"])

            if dates is None or close is None:
                raise ValueError(
                    "数据缺少日期列或收盘价列，"
                    f"当前列名: {list(df.columns)}"
                )

            dates = pd.to_datetime(dates)
            close = pd.to_numeric(close, errors="coerce")

            # 计算回撤
            cummax = close.cummax()
            drawdown = (close - cummax) / cummax * 100  # 转换为百分比

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.fill_between(dates, drawdown, 0, color="salmon", alpha=0.4)
            ax.plot(dates, drawdown, color="red", linewidth=1.0, label="回撤")

            # 标注最大回撤
            max_dd_idx = drawdown.idxmin()
            max_dd_value = drawdown.min()
            if not pd.isna(max_dd_value):
                ax.annotate(
                    f"最大回撤: {max_dd_value:.2f}%",
                    xy=(dates.iloc[max_dd_idx] if isinstance(max_dd_idx, int)
                        else dates[max_dd_idx], max_dd_value),
                    xytext=(30, 20),
                    textcoords="offset points",
                    fontsize=10,
                    arrowprops=dict(arrowstyle="->", color="black"),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
                )

            title = f"{symbol} 回撤曲线" if symbol else "回撤曲线"
            ax.set_title(title, fontsize=14)
            ax.set_xlabel("日期", fontsize=12)
            ax.set_ylabel("回撤 (%)", fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(True, linestyle="--", alpha=0.7)

            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=150, bbox_inches="tight")
                logger.info("回撤曲线图已保存至: %s", save_path)

            if show:
                plt.show()

            logger.info("回撤曲线图绘制完成，ETF代码: %s，最大回撤: %.2f%%",
                        symbol, max_dd_value if not pd.isna(max_dd_value) else 0)
            return fig

        except ValueError:
            raise
        except Exception as e:
            logger.error("绘制回撤曲线图时发生错误: %s", e)
            raise

    @staticmethod
    def _extract_column(df, candidate_names):
        """从 DataFrame 中根据候选列名列表提取数据列。

        按照候选列名列表的顺序依次查找，返回第一个匹配列的数据。

        Args:
            df (pd.DataFrame): 数据源 DataFrame。
            candidate_names (list[str]): 候选列名列表，按优先级排序。

        Returns:
            pd.Series or None: 匹配到的列数据，如果没有匹配则返回 None。
        """
        for name in candidate_names:
            if name in df.columns:
                return df[name]
        return None

    @staticmethod
    def _extract_column_name(df, candidate_names):
        """从 DataFrame 中根据候选列名列表查找实际列名。

        按照候选列名列表的顺序依次查找，返回第一个匹配的实际列名。

        Args:
            df (pd.DataFrame): 数据源 DataFrame。
            candidate_names (list[str]): 候选列名列表，按优先级排序。

        Returns:
            str or None: 匹配到的实际列名，如果没有匹配则返回 None。
        """
        for name in candidate_names:
            if name in df.columns:
                return name
        return None
