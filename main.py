# -*- coding: utf-8 -*-
"""
ETF分析工具命令行交互入口模块

本模块提供基于命令行的交互式ETF分析工具，包含数据获取、数据分析、
数据可视化和报告生成四大功能模块，用户通过菜单导航完成各项操作。
"""

import re
import os
from datetime import datetime

from etf_analyzer.config import ensure_dirs, REPORT_DIR_PATH, DEFAULT_START_DATE
from etf_analyzer.logger import setup_logger
from etf_analyzer.data_fetcher import ETFDataFetcher
from etf_analyzer.data_processor import DataProcessor
from etf_analyzer.analyzer import ETFAnalyzer
from etf_analyzer.visualizer import ETFVisualizer
from etf_analyzer.report_generator import ReportGenerator, AVAILABLE_MODULES


class ETFCLI:
    """ETF分析工具命令行交互类，封装所有用户交互逻辑。

    通过菜单导航的方式，提供数据获取、数据分析、数据可视化和报告生成
    四大核心功能，支持输入验证、异常处理和日志记录。

    Attributes:
        fetcher: ETFDataFetcher 实例，用于获取ETF数据。
        processor: DataProcessor 实例，用于数据处理。
        analyzer: ETFAnalyzer 实例，用于ETF分析。
        visualizer: ETFVisualizer 实例，用于数据可视化。
        report_generator: ReportGenerator 实例，用于生成报告。
        logger: 日志记录器实例。
    """

    # ANSI 颜色码
    _COLOR_RED = "\033[91m"       # 红色 - 正值（中国金融惯例：涨=红）
    _COLOR_GREEN = "\033[92m"     # 绿色 - 负值（中国金融惯例：跌=绿）
    _COLOR_YELLOW = "\033[93m"    # 黄色 - 警告/中性值
    _COLOR_CYAN = "\033[96m"      # 青色 - 标题/标签
    _COLOR_BOLD = "\033[1m"       # 加粗
    _COLOR_RESET = "\033[0m"      # 重置颜色

    # 主菜单选项映射
    MAIN_MENU = {
        "1": "数据获取",
        "2": "数据分析",
        "3": "数据可视化",
        "4": "报告生成",
        "0": "退出",
    }

    # 数据获取子菜单选项映射
    DATA_FETCH_MENU = {
        "1": "查询ETF列表",
        "2": "获取实时行情",
        "3": "获取历史数据",
        "4": "获取持仓信息",
        "0": "返回主菜单",
    }

    # 数据分析子菜单选项映射
    DATA_ANALYSIS_MENU = {
        "1": "净值走势分析",
        "2": "成分股构成分析",
        "3": "行业分布统计",
        "4": "风险指标计算",
        "5": "绩效分析",
        "0": "返回主菜单",
    }

    # 数据可视化子菜单选项映射
    DATA_VIS_MENU = {
        "1": "K线图",
        "2": "净值走势图",
        "3": "行业分布饼图",
        "4": "成分股权重柱状图",
        "5": "回撤曲线图",
        "0": "返回主菜单",
    }

    # 报告生成子菜单选项映射
    REPORT_MENU = {
        "1": "生成完整分析报告",
        "2": "生成自定义报告",
        "0": "返回主菜单",
    }

    def __init__(self):
        """初始化ETFCLI实例。

        创建各功能模块的实例，初始化日志记录器，
        并确保项目所需的目录结构存在。
        """
        ensure_dirs()
        self.logger = setup_logger("cli")
        self.fetcher = ETFDataFetcher()
        self.processor = DataProcessor()
        self.analyzer = ETFAnalyzer()
        self.visualizer = ETFVisualizer()
        self.report_generator = ReportGenerator()
        self.logger.info("ETFCLI 初始化完成")

    # ------------------------------------------------------------------
    # 通用辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _print_separator(char="=", length=40):
        """打印分隔线。

        根据指定字符和长度输出一条分隔线，用于美化控制台输出。

        Args:
            char (str): 分隔线使用的字符，默认为 "="。
            length (int): 分隔线长度，默认为 40。
        """
        print(char * length)

    @staticmethod
    def _print_menu(title, menu_dict):
        """打印格式化菜单。

        以美观的格式输出菜单标题和选项列表，包含上下分隔线。

        Args:
            title (str): 菜单标题文字。
            menu_dict (dict): 菜单选项字典，键为选项编号，值为选项描述。
        """
        print()
        print(f"--- {title} ---")
        for key, value in menu_dict.items():
            print(f"  {key}. {value}")
        print()

    @staticmethod
    def _color_value(value):
        """根据数值正负返回带 ANSI 颜色的字符串。

        中国金融行业惯例：正值（涨）显示红色，负值（跌）显示绿色。
        零值或无法解析的非数值返回默认颜色。

        Args:
            value: 待着色的数值或字符串。

        Returns:
            str: 带 ANSI 颜色码的数值字符串（已包含重置码）。
        """
        try:
            num = float(value)
            if num > 0:
                return f"{ETFCLI._COLOR_RED}{value}{ETFCLI._COLOR_RESET}"
            elif num < 0:
                return f"{ETFCLI._COLOR_GREEN}{value}{ETFCLI._COLOR_RESET}"
            else:
                return str(value)
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_number(value, decimals=4, as_percentage=False):
        """格式化数值，消除科学计数法，按精度显示可读数字。

        将科学计数法（如 1.23e-04）转为常规小数（0.0001），
        避免 e 符号影响终端阅读体验。支持百分比和纯小数两种模式。

        Args:
            value: 数值或字符串。
            decimals (int): 小数位数，默认为 4。
            as_percentage (bool): 是否以百分比形式显示，
                True 时会将数值乘以 100 并追加 %% 符号。

        Returns:
            str: 格式化后的数字字符串，不含科学计数法。
        """
        try:
            num = float(value)
            if as_percentage:
                return f"{num * 100:.{decimals}f}%"
            return f"{num:.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _get_input(prompt):
        """获取用户输入，自动去除首尾空白。

        显示提示信息并等待用户输入，返回去除首尾空白后的字符串。

        Args:
            prompt (str): 输入提示文字。

        Returns:
            str: 用户输入的内容（已去除首尾空白）。
        """
        return input(prompt).strip()

    @staticmethod
    def _validate_symbol(symbol):
        """验证ETF代码格式是否合法。

        ETF代码应为6位数字，如 "510300"、"159919" 等。

        Args:
            symbol (str): 待验证的ETF代码字符串。

        Returns:
            bool: 格式合法返回 True，否则返回 False。
        """
        return bool(re.match(r"^\d{6}$", symbol))

    @staticmethod
    def _validate_date(date_str):
        """验证日期格式是否合法。

        日期格式应为 YYYYMMDD，且为有效的日历日期。

        Args:
            date_str (str): 待验证的日期字符串。

        Returns:
            bool: 格式合法且日期有效返回 True，否则返回 False。
        """
        if not re.match(r"^\d{8}$", date_str):
            return False
        try:
            datetime.strptime(date_str, "%Y%m%d")
            return True
        except ValueError:
            return False

    def _input_symbol(self, prompt="请输入ETF代码: "):
        """循环获取并验证ETF代码输入。

        反复提示用户输入ETF代码，直到输入格式合法为止。
        合法的ETF代码为6位数字。

        Args:
            prompt (str): 输入提示文字，默认为 "请输入ETF代码: "。

        Returns:
            str: 合法的ETF代码字符串。
        """
        while True:
            symbol = self._get_input(prompt)
            if self._validate_symbol(symbol):
                return symbol
            print("  [错误] ETF代码格式不正确，应为6位数字（如 510300），请重新输入。")

    def _input_date(self, prompt, allow_empty=False, default=None):
        """循环获取并验证日期输入。

        反复提示用户输入日期，直到格式合法为止。
        日期格式为 YYYYMMDD。

        Args:
            prompt (str): 输入提示文字，应包含格式提示。
            allow_empty (bool): 是否允许空输入，默认为 False。
                当允许空输入且用户直接回车时，返回 default 值。
            default (str, optional): 空输入时的默认返回值，默认为 None。

        Returns:
            str: 合法的日期字符串（YYYYMMDD格式）或默认值。
        """
        while True:
            date_str = self._get_input(prompt)
            if allow_empty and date_str == "":
                return default
            if self._validate_date(date_str):
                return date_str
            print("  [错误] 日期格式不正确，应为 YYYYMMDD 格式（如 20240101），请重新输入。")

    # ------------------------------------------------------------------
    # 主运行循环
    # ------------------------------------------------------------------

    def run(self):
        """运行命令行交互主循环。

        显示主菜单并根据用户选择进入对应的功能子模块，
        直到用户选择退出为止。
        """
        self.logger.info("ETF分析工具启动")
        while True:
            self._print_separator()
            print("    ETF 分析工具 v1.0")
            self._print_separator()
            self._print_menu("主菜单", self.MAIN_MENU)

            choice = self._get_input("请选择功能 [0-4]: ")
            if choice == "1":
                self._menu_data_fetch()
            elif choice == "2":
                self._menu_data_analysis()
            elif choice == "3":
                self._menu_data_visual()
            elif choice == "4":
                self._menu_report()
            elif choice == "0":
                print("\n  感谢使用 ETF 分析工具，再见！")
                self.logger.info("ETF分析工具退出")
                break
            else:
                print("  [错误] 无效选择，请输入 0-4 之间的数字。")

    # ------------------------------------------------------------------
    # 子菜单1：数据获取
    # ------------------------------------------------------------------

    def _menu_data_fetch(self):
        """数据获取子菜单交互循环。

        显示数据获取子菜单，根据用户选择执行对应的操作，
        包括查询ETF列表、获取实时行情、获取历史数据和获取持仓信息。
        """
        while True:
            self._print_menu("数据获取", self.DATA_FETCH_MENU)
            choice = self._get_input("请选择功能 [0-4]: ")

            if choice == "1":
                self._fetch_etf_list()
            elif choice == "2":
                self._fetch_realtime_quote()
            elif choice == "3":
                self._fetch_history_data()
            elif choice == "4":
                self._fetch_holdings()
            elif choice == "0":
                break
            else:
                print("  [错误] 无效选择，请输入 0-4 之间的数字。")

    def _fetch_etf_list(self):
        """查询ETF列表。

        提示用户输入关键词，调用数据获取器搜索ETF列表，
        并以表格形式展示搜索结果。如果未输入关键词则返回全部ETF。
        """
        keyword = self._get_input("请输入搜索关键词（直接回车查看全部）: ")
        self.logger.info("查询ETF列表，关键词: %s", keyword or "全部")

        try:
            df = self.fetcher.get_etf_list(keyword=keyword if keyword else None)
            if df is None or df.empty:
                print("  [提示] 未找到匹配的ETF数据。")
                return

            # 显示前20条结果
            display_cols = ["代码", "名称", "最新价", "涨跌幅", "成交额"]
            available_cols = [c for c in display_cols if c in df.columns]
            display_df = df[available_cols].head(20)

            print(f"\n  共找到 {len(df)} 条记录，显示前 {min(20, len(df))} 条：")
            self._print_separator("=", 70)
            print(display_df.to_string(index=False))
            self._print_separator("=", 70)

        except Exception as e:
            print(f"  [错误] 查询ETF列表失败: {e}")
            self.logger.error("查询ETF列表失败: %s", e)

    def _fetch_realtime_quote(self):
        """获取ETF实时行情。

        提示用户输入ETF代码，调用数据获取器获取实时行情数据，
        并以格式化方式展示各项行情指标。
        """
        symbol = self._input_symbol()
        self.logger.info("获取实时行情，ETF代码: %s", symbol)

        try:
            quote = self.fetcher.get_realtime_quote(symbol)
            if not quote:
                print(f"  [提示] 未找到代码为 {symbol} 的ETF实时行情。")
                return

            name = quote.get('name', '')
            print(f"\n  {self._COLOR_CYAN}{name}（{symbol}）实时行情：{self._COLOR_RESET}")
            self._print_separator("=", 48)
            print(f"  最新价  | {quote.get('price', '—')}")
            change_pct = quote.get('change_pct', '—')
            colored_pct = self._color_value(change_pct) if change_pct != '—' else change_pct
            print(f"  涨跌幅  | {colored_pct}%")
            change_amt = quote.get('change_amt', '—')
            colored_amt = self._color_value(change_amt) if change_amt != '—' else change_amt
            print(f"  涨跌额  | {colored_amt}")
            print(f"  开盘价  | {quote.get('open', '—')}")
            print(f"  最高价  | {quote.get('high', '—')}")
            print(f"  最低价  | {quote.get('low', '—')}")
            print(f"  昨收价  | {quote.get('prev_close', '—')}")
            print(f"  成交量  | {quote.get('volume', '—')}")
            print(f"  成交额  | {quote.get('amount', '—')}")
            self._print_separator("=", 48)

        except Exception as e:
            print(f"  [错误] 获取实时行情失败: {e}")
            self.logger.error("获取实时行情失败: %s", e)

    def _fetch_history_data(self):
        """获取ETF历史数据。

        提示用户输入ETF代码、起始日期和结束日期，
        调用数据获取器获取历史K线数据，并展示数据概况。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        self.logger.info(
            "获取历史数据，ETF代码: %s，起始: %s，结束: %s",
            symbol, start_date, end_date,
        )

        try:
            df = self.fetcher.get_history_data(
                symbol, start_date=start_date, end_date=end_date,
            )
            if df is None or df.empty:
                print(f"  [提示] 未获取到代码为 {symbol} 的历史数据。")
                return

            print(f"\n  {self._COLOR_CYAN}{symbol} 历史数据概况：{self._COLOR_RESET}")
            self._print_separator("=", 50)
            print(f"  数据条数  | {len(df)}")
            print(f"  时间范围  | {start_date} ~ {end_date}")
            print(f"  数据列    | {', '.join(df.columns.tolist())}")
            self._print_separator("-", 50)

            # 显示前5条和后5条
            print("\n  前5条数据：")
            print(df.head(5).to_string(index=False))
            print("\n  后5条数据：")
            print(df.tail(5).to_string(index=False))

        except Exception as e:
            print(f"  [错误] 获取历史数据失败: {e}")
            self.logger.error("获取历史数据失败: %s", e)

    def _fetch_holdings(self):
        """获取ETF持仓信息。

        提示用户输入ETF代码，调用数据获取器获取持仓数据，
        并以表格形式展示持仓列表。
        """
        symbol = self._input_symbol()
        self.logger.info("获取持仓信息，ETF代码: %s", symbol)

        try:
            df = self.fetcher.get_etf_holdings(symbol)
            if df is None or df.empty:
                print(f"  [提示] 未获取到代码为 {symbol} 的持仓信息。")
                return

            print(f"\n  {self._COLOR_CYAN}{symbol} 持仓信息（共 {len(df)} 条）：{self._COLOR_RESET}")
            self._print_separator("=", 70)
            print(df.head(20).to_string(index=False))
            self._print_separator("=", 70)

        except Exception as e:
            print(f"  [错误] 获取持仓信息失败: {e}")
            self.logger.error("获取持仓信息失败: %s", e)

    # ------------------------------------------------------------------
    # 子菜单2：数据分析
    # ------------------------------------------------------------------

    def _menu_data_analysis(self):
        """数据分析子菜单交互循环。

        显示数据分析子菜单，根据用户选择执行对应的操作，
        包括净值走势分析、成分股构成分析、行业分布统计、
        风险指标计算和绩效分析。
        """
        while True:
            self._print_menu("数据分析", self.DATA_ANALYSIS_MENU)
            choice = self._get_input("请选择功能 [0-5]: ")

            if choice == "1":
                self._analyze_nav_trend()
            elif choice == "2":
                self._analyze_holdings()
            elif choice == "3":
                self._analyze_industry()
            elif choice == "4":
                self._analyze_risk()
            elif choice == "5":
                self._analyze_performance()
            elif choice == "0":
                break
            else:
                print("  [错误] 无效选择，请输入 0-5 之间的数字。")

    def _analyze_nav_trend(self):
        """净值走势分析。

        提示用户输入ETF代码和日期范围，调用分析器执行净值走势分析，
        展示累计收益率、年化收益率和趋势判断等结果。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        self.logger.info(
            "净值走势分析，ETF代码: %s，起始: %s，结束: %s",
            symbol, start_date, end_date,
        )

        try:
            result = self.analyzer.analyze_nav_trend(
                symbol, start_date=start_date, end_date=end_date,
            )
            if not result:
                print(f"  [提示] 净值走势分析失败，未获取到有效数据。")
                return

            print(f"\n  {self._COLOR_CYAN}{symbol} 净值走势分析结果：{self._COLOR_RESET}")
            self._print_separator("=", 48)
            cum_ret = result['cumulative_return']
            ann_ret = result['annualized_return']
            print(f"  累计收益率  | {self._color_value(self._format_number(cum_ret / 100, 2, as_percentage=True))}")
            print(f"  年化收益率  | {self._color_value(self._format_number(ann_ret, 2, as_percentage=True))}")
            trend_text = result['trend']
            trend_colored = (f"{self._COLOR_RED}{trend_text}{self._COLOR_RESET}"
                             if "上升" in trend_text else
                             f"{self._COLOR_GREEN}{trend_text}{self._COLOR_RESET}"
                             if "下降" in trend_text else trend_text)
            print(f"  趋势判断    | {trend_colored}")
            self._print_separator("=", 48)

        except Exception as e:
            print(f"  [错误] 净值走势分析失败: {e}")
            self.logger.error("净值走势分析失败: %s", e)

    def _analyze_holdings(self):
        """成分股构成分析。

        提示用户输入ETF代码，调用分析器执行成分股构成分析，
        展示前十大权重股和持仓集中度。
        """
        symbol = self._input_symbol()
        self.logger.info("成分股构成分析，ETF代码: %s", symbol)

        try:
            result = self.analyzer.analyze_holdings(symbol)
            if not result:
                print("  [提示] 成分股构成分析失败，未获取到有效数据。")
                return

            top10 = result["top10_holdings"]
            concentration = result["concentration_ratio"]

            print(f"\n  {self._COLOR_CYAN}{symbol} 成分股构成分析结果：{self._COLOR_RESET}")
            self._print_separator("=", 60)
            print(f"  持仓集中度（前十大） | {self._format_number(concentration * 100, 1)}%")
            print(f"\n  前十大权重股：")
            print(top10.to_string(index=False))
            self._print_separator("=", 60)

        except Exception as e:
            print(f"  [错误] 成分股构成分析失败: {e}")
            self.logger.error("成分股构成分析失败: %s", e)

    def _analyze_industry(self):
        """行业分布统计。

        提示用户输入ETF代码，调用分析器执行行业分布统计，
        展示各行业持仓占比和行业数量。
        """
        symbol = self._input_symbol()
        self.logger.info("行业分布统计，ETF代码: %s", symbol)

        try:
            result = self.analyzer.analyze_industry_distribution(symbol)
            if not result:
                print("  [提示] 行业分布统计失败，未获取到有效数据。")
                return

            industry_dist = result["industry_distribution"]
            industry_count = result["industry_count"]

            print(f"\n  {self._COLOR_CYAN}{symbol} 行业分布统计结果：{self._COLOR_RESET}")
            self._print_separator("=", 50)
            print(f"  行业数量  | {industry_count}")
            print(f"\n  行业持仓占比：")
            print(industry_dist.to_string(index=False))
            self._print_separator("=", 50)

        except Exception as e:
            print(f"  [错误] 行业分布统计失败: {e}")
            self.logger.error("行业分布统计失败: %s", e)

    def _analyze_risk(self):
        """风险指标计算。

        提示用户输入ETF代码、日期范围和可选的基准代码，
        调用分析器计算风险指标，展示波动率、最大回撤、夏普比率等结果。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        benchmark_input = self._get_input(
            "请输入基准指数代码（6位数字，直接回车跳过）: "
        )
        benchmark_symbol = None
        if benchmark_input:
            if self._validate_symbol(benchmark_input):
                benchmark_symbol = benchmark_input
            else:
                print("  [警告] 基准代码格式不正确，将跳过信息比率计算。")

        self.logger.info(
            "风险指标计算，ETF代码: %s，基准: %s", symbol, benchmark_symbol or "无",
        )

        try:
            result = self.analyzer.calculate_risk_metrics(
                symbol, start_date=start_date, end_date=end_date,
                benchmark_symbol=benchmark_symbol,
            )
            if not result:
                print("  [提示] 风险指标计算失败，未获取到有效数据。")
                return

            print(f"\n  {self._COLOR_CYAN}{symbol} 风险指标计算结果：{self._COLOR_RESET}")
            self._print_separator("=", 55)
            print(f"  日波动率         | {self._format_number(result['daily_volatility'], 6)}")
            print(f"  年化波动率       | {self._format_number(result['annualized_volatility'], 4)}")
            max_dd = result['max_drawdown']
            print(f"  最大回撤         | {self._color_value(self._format_number(max_dd, 2, as_percentage=True))}")
            print(f"  最大回撤起始     | {result['max_drawdown_start']}")
            print(f"  最大回撤结束     | {result['max_drawdown_end']}")
            sharpe = result['sharpe_ratio']
            print(f"  夏普比率         | {self._color_value(self._format_number(sharpe, 4))}")
            if result["information_ratio"] is not None:
                ir = result['information_ratio']
                print(f"  信息比率         | {self._color_value(self._format_number(ir, 4))}")
            else:
                print("  信息比率         | 未计算（未提供基准代码）")
            self._print_separator("=", 55)

        except Exception as e:
            print(f"  [错误] 风险指标计算失败: {e}")
            self.logger.error("风险指标计算失败: %s", e)

    def _analyze_performance(self):
        """绩效分析。

        提示用户输入ETF代码、基准代码和日期范围，
        调用分析器执行绩效分析，展示超额收益、跟踪误差、信息比率和胜率。
        """
        symbol = self._input_symbol()
        benchmark_symbol = self._input_symbol("请输入基准指数代码: ")
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        self.logger.info(
            "绩效分析，ETF代码: %s，基准: %s，起始: %s，结束: %s",
            symbol, benchmark_symbol, start_date, end_date,
        )

        try:
            result = self.analyzer.analyze_performance(
                symbol, benchmark_symbol,
                start_date=start_date, end_date=end_date,
            )
            if not result:
                print("  [提示] 绩效分析失败，未获取到有效数据。")
                return

            print(f"\n  {self._COLOR_CYAN}{symbol} 绩效分析结果（基准: {benchmark_symbol}）：{self._COLOR_RESET}")
            self._print_separator("=", 55)
            excess_ret = result['excess_return']
            print(f"  超额收益    | {self._color_value(self._format_number(excess_ret / 100, 2, as_percentage=True))}")
            print(f"  跟踪误差    | {self._format_number(result['tracking_error'], 4)}")
            ir = result['information_ratio']
            print(f"  信息比率    | {self._color_value(self._format_number(ir, 4))}")
            print(f"  胜率        | {self._format_number(result['win_rate'] * 100, 1)}%")
            self._print_separator("=", 55)

        except Exception as e:
            print(f"  [错误] 绩效分析失败: {e}")
            self.logger.error("绩效分析失败: %s", e)

    # ------------------------------------------------------------------
    # 子菜单3：数据可视化
    # ------------------------------------------------------------------

    def _menu_data_visual(self):
        """数据可视化子菜单交互循环。

        显示数据可视化子菜单，根据用户选择生成对应的图表，
        图表保存到 reports/ 目录下。
        """
        while True:
            self._print_menu("数据可视化", self.DATA_VIS_MENU)
            choice = self._get_input("请选择功能 [0-5]: ")

            if choice == "1":
                self._visual_kline()
            elif choice == "2":
                self._visual_nav_trend()
            elif choice == "3":
                self._visual_industry_pie()
            elif choice == "4":
                self._visual_holdings_bar()
            elif choice == "5":
                self._visual_drawdown()
            elif choice == "0":
                break
            else:
                print("  [错误] 无效选择，请输入 0-5 之间的数字。")

    def _get_save_path(self, symbol, chart_type, ext="png"):
        """生成图表保存路径。

        根据ETF代码、图表类型和文件扩展名，在 reports/ 目录下
        生成唯一的文件保存路径，避免文件名冲突。

        Args:
            symbol (str): ETF代码。
            chart_type (str): 图表类型标识，如 "kline"、"nav_trend" 等。
            ext (str): 文件扩展名，默认为 "png"。

        Returns:
            str: 图表文件的绝对路径。
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{chart_type}_{timestamp}.{ext}"
        return os.path.join(REPORT_DIR_PATH, filename)

    def _visual_kline(self):
        """绘制K线图。

        提示用户输入ETF代码和日期范围，获取历史数据后绘制K线图，
        保存到 reports/ 目录。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        self.logger.info("绘制K线图，ETF代码: %s", symbol)

        try:
            df = self.fetcher.get_history_data(
                symbol, start_date=start_date, end_date=end_date,
            )
            if df is None or df.empty:
                print("  [提示] 未获取到历史数据，无法绘制K线图。")
                return

            save_path = self._get_save_path(symbol, "kline")
            self.visualizer.plot_kline(df, symbol=symbol, save_path=save_path, show=False)
            print(f"  [成功] K线图已保存至: {save_path}")

        except Exception as e:
            print(f"  [错误] 绘制K线图失败: {e}")
            self.logger.error("绘制K线图失败: %s", e)

    def _visual_nav_trend(self):
        """绘制净值走势图。

        提示用户输入ETF代码和日期范围，执行净值走势分析后绘制净值走势图，
        保存到 reports/ 目录。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        self.logger.info("绘制净值走势图，ETF代码: %s", symbol)

        try:
            result = self.analyzer.analyze_nav_trend(
                symbol, start_date=start_date, end_date=end_date,
            )
            if not result or result.get("nav_data") is None:
                print("  [提示] 净值走势分析失败，无法绘制走势图。")
                return

            nav_data = result["nav_data"]
            save_path = self._get_save_path(symbol, "nav_trend")
            self.visualizer.plot_nav_trend(
                nav_data, symbol=symbol, save_path=save_path, show=False,
            )
            print(f"  [成功] 净值走势图已保存至: {save_path}")

        except Exception as e:
            print(f"  [错误] 绘制净值走势图失败: {e}")
            self.logger.error("绘制净值走势图失败: %s", e)

    def _visual_industry_pie(self):
        """绘制行业分布饼图。

        提示用户输入ETF代码，执行行业分布统计后绘制饼图，
        保存到 reports/ 目录。
        """
        symbol = self._input_symbol()
        self.logger.info("绘制行业分布饼图，ETF代码: %s", symbol)

        try:
            result = self.analyzer.analyze_industry_distribution(symbol)
            if not result or result.get("industry_distribution") is None:
                print("  [提示] 行业分布统计失败，无法绘制饼图。")
                return

            industry_data = result["industry_distribution"]
            save_path = self._get_save_path(symbol, "industry_pie")
            self.visualizer.plot_industry_pie(
                industry_data, symbol=symbol, save_path=save_path, show=False,
            )
            print(f"  [成功] 行业分布饼图已保存至: {save_path}")

        except Exception as e:
            print(f"  [错误] 绘制行业分布饼图失败: {e}")
            self.logger.error("绘制行业分布饼图失败: %s", e)

    def _visual_holdings_bar(self):
        """绘制成分股权重柱状图。

        提示用户输入ETF代码，执行成分股构成分析后绘制柱状图，
        保存到 reports/ 目录。
        """
        symbol = self._input_symbol()
        self.logger.info("绘制成分股权重柱状图，ETF代码: %s", symbol)

        try:
            result = self.analyzer.analyze_holdings(symbol)
            if not result or result.get("top10_holdings") is None:
                print("  [提示] 成分股构成分析失败，无法绘制柱状图。")
                return

            holdings_data = result["top10_holdings"]
            save_path = self._get_save_path(symbol, "holdings_bar")
            self.visualizer.plot_holdings_bar(
                holdings_data, symbol=symbol, save_path=save_path, show=False,
            )
            print(f"  [成功] 成分股权重柱状图已保存至: {save_path}")

        except Exception as e:
            print(f"  [错误] 绘制成分股权重柱状图失败: {e}")
            self.logger.error("绘制成分股权重柱状图失败: %s", e)

    def _visual_drawdown(self):
        """绘制回撤曲线图。

        提示用户输入ETF代码和日期范围，获取历史数据后绘制回撤曲线图，
        保存到 reports/ 目录。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        self.logger.info("绘制回撤曲线图，ETF代码: %s", symbol)

        try:
            df = self.fetcher.get_history_data(
                symbol, start_date=start_date, end_date=end_date,
            )
            if df is None or df.empty:
                print("  [提示] 未获取到历史数据，无法绘制回撤曲线图。")
                return

            save_path = self._get_save_path(symbol, "drawdown")
            self.visualizer.plot_drawdown(
                df, symbol=symbol, save_path=save_path, show=False,
            )
            print(f"  [成功] 回撤曲线图已保存至: {save_path}")

        except Exception as e:
            print(f"  [错误] 绘制回撤曲线图失败: {e}")
            self.logger.error("绘制回撤曲线图失败: %s", e)

    # ------------------------------------------------------------------
    # 子菜单4：报告生成
    # ------------------------------------------------------------------

    def _menu_report(self):
        """报告生成子菜单交互循环。

        显示报告生成子菜单，根据用户选择生成完整或自定义的PDF分析报告。
        """
        while True:
            self._print_menu("报告生成", self.REPORT_MENU)
            choice = self._get_input("请选择功能 [0-2]: ")

            if choice == "1":
                self._generate_full_report()
            elif choice == "2":
                self._generate_custom_report()
            elif choice == "0":
                break
            else:
                print("  [错误] 无效选择，请输入 0-2 之间的数字。")

    def _collect_analysis_results(self, symbol, start_date=None, end_date=None,
                                  benchmark_symbol=None):
        """收集ETF分析所需的全部数据和分析结果。

        按顺序执行净值走势分析、成分股构成分析、行业分布统计、
        风险指标计算等操作，将结果汇总为一个字典供报告生成器使用。

        Args:
            symbol (str): ETF代码。
            start_date (str, optional): 起始日期，格式 YYYYMMDD。
            end_date (str, optional): 结束日期，格式 YYYYMMDD。
            benchmark_symbol (str, optional): 基准指数代码。

        Returns:
            dict: 包含各模块分析结果的字典，键包括：
                nav_data, holdings_data, industry_data,
                risk_metrics, performance_metrics 等。
        """
        results = {}
        self.logger.info("开始收集分析数据，ETF代码: %s", symbol)

        # 净值走势分析
        print("  [1/4] 正在执行净值走势分析...")
        nav_result = self.analyzer.analyze_nav_trend(
            symbol, start_date=start_date, end_date=end_date,
        )
        if nav_result:
            results["nav_data"] = nav_result.get("nav_data")
            results["performance_metrics"] = {
                "cumulative_return": nav_result.get("cumulative_return"),
                "annualized_return": nav_result.get("annualized_return"),
            }

        # 成分股构成分析
        print("  [2/4] 正在执行成分股构成分析...")
        holdings_result = self.analyzer.analyze_holdings(symbol)
        if holdings_result:
            results["holdings_data"] = holdings_result.get("top10_holdings")

        # 行业分布统计
        print("  [3/4] 正在执行行业分布统计...")
        industry_result = self.analyzer.analyze_industry_distribution(symbol)
        if industry_result:
            results["industry_data"] = industry_result.get("industry_distribution")

        # 风险指标计算
        print("  [4/4] 正在计算风险指标...")
        risk_result = self.analyzer.calculate_risk_metrics(
            symbol, start_date=start_date, end_date=end_date,
            benchmark_symbol=benchmark_symbol,
        )
        if risk_result:
            results["risk_metrics"] = risk_result

        # 绩效分析（需要基准代码）
        if benchmark_symbol:
            print("  [额外] 正在执行绩效分析...")
            perf_result = self.analyzer.analyze_performance(
                symbol, benchmark_symbol,
                start_date=start_date, end_date=end_date,
            )
            if perf_result:
                results["performance_metrics"] = {
                    "cumulative_return": nav_result.get("cumulative_return") if nav_result else None,
                    "annualized_return": nav_result.get("annualized_return") if nav_result else None,
                    "excess_return": perf_result.get("excess_return"),
                    "tracking_error": perf_result.get("tracking_error"),
                    "information_ratio": perf_result.get("information_ratio"),
                    "win_rate": perf_result.get("win_rate"),
                }

        self.logger.info("分析数据收集完成，ETF代码: %s", symbol)
        return results

    def _generate_full_report(self):
        """生成完整分析报告。

        提示用户输入ETF代码和日期范围，收集全部分析数据后，
        生成包含所有模块的PDF分析报告。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        benchmark_input = self._get_input(
            "请输入基准指数代码（6位数字，直接回车跳过）: "
        )
        benchmark_symbol = None
        if benchmark_input and self._validate_symbol(benchmark_input):
            benchmark_symbol = benchmark_input

        self.logger.info("生成完整报告，ETF代码: %s", symbol)

        try:
            print(f"\n  正在收集 {symbol} 的分析数据，请稍候...")
            analysis_results = self._collect_analysis_results(
                symbol, start_date=start_date, end_date=end_date,
                benchmark_symbol=benchmark_symbol,
            )

            if not analysis_results:
                print("  [提示] 未能收集到任何分析数据，无法生成报告。")
                return

            output_path = self.report_generator.generate_report(
                symbol, analysis_results, modules=None,
            )
            print(f"\n  [成功] 完整分析报告已生成: {output_path}")

        except Exception as e:
            print(f"  [错误] 生成完整报告失败: {e}")
            self.logger.error("生成完整报告失败: %s", e)

    def _generate_custom_report(self):
        """生成自定义报告。

        提示用户输入ETF代码和日期范围，然后选择要包含的报告模块，
        生成仅包含所选模块的PDF分析报告。
        """
        symbol = self._input_symbol()
        start_date = self._input_date(
            f"请输入起始日期（YYYYMMDD，默认 {DEFAULT_START_DATE}）: ",
            allow_empty=True,
            default=DEFAULT_START_DATE,
        )
        end_date = self._input_date(
            "请输入结束日期（YYYYMMDD，默认今天）: ",
            allow_empty=True,
            default=datetime.now().strftime("%Y%m%d"),
        )
        benchmark_input = self._get_input(
            "请输入基准指数代码（6位数字，直接回车跳过）: "
        )
        benchmark_symbol = None
        if benchmark_input and self._validate_symbol(benchmark_input):
            benchmark_symbol = benchmark_input

        # 模块选择
        module_labels = {
            "nav_trend": "净值走势分析",
            "holdings": "成分股构成分析",
            "industry": "行业分布统计",
            "risk": "风险指标计算",
            "performance": "绩效分析",
        }
        print("\n  可选报告模块：")
        for i, (key, label) in enumerate(module_labels.items(), 1):
            print(f"    {i}. {label}")

        selected = self._get_input(
            "请选择要包含的模块（输入编号，多个用逗号分隔，如 1,3,5）: "
        )

        # 解析用户选择的模块
        selected_modules = []
        try:
            indices = [int(x.strip()) for x in selected.split(",") if x.strip()]
            module_keys = list(module_labels.keys())
            for idx in indices:
                if 1 <= idx <= len(module_keys):
                    selected_modules.append(module_keys[idx - 1])
                else:
                    print(f"  [警告] 编号 {idx} 超出范围，已忽略。")
        except ValueError:
            print("  [错误] 输入格式不正确，将生成包含所有模块的报告。")
            selected_modules = None

        if not selected_modules:
            selected_modules = None

        self.logger.info(
            "生成自定义报告，ETF代码: %s，模块: %s",
            symbol, selected_modules or "全部",
        )

        try:
            print(f"\n  正在收集 {symbol} 的分析数据，请稍候...")
            analysis_results = self._collect_analysis_results(
                symbol, start_date=start_date, end_date=end_date,
                benchmark_symbol=benchmark_symbol,
            )

            if not analysis_results:
                print("  [提示] 未能收集到任何分析数据，无法生成报告。")
                return

            output_path = self.report_generator.generate_report(
                symbol, analysis_results, modules=selected_modules,
            )
            print(f"\n  [成功] 自定义分析报告已生成: {output_path}")

        except Exception as e:
            print(f"  [错误] 生成自定义报告失败: {e}")
            self.logger.error("生成自定义报告失败: %s", e)


if __name__ == "__main__":
    cli = ETFCLI()
    cli.run()
