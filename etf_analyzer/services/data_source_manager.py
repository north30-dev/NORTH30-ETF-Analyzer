# -*- coding: utf-8 -*-
"""
数据源管理器模块

提供数据源的注册、优先级排序、健康检查和自动故障转移功能，
支持多数据源的统一管理和透明切换。
"""

import time
import threading

import pandas as pd

from config import DATASOURCE_PRIORITY, DATASOURCE_HEALTH_CHECK_INTERVAL
from etf_analyzer.data_sources.base import BaseDataSource
from etf_analyzer.data_sources.akshare_source import AkshareDataSource
from etf_analyzer.data_sources.baostock_source import BaostockDataSource
from etf_analyzer.data_sources.pytdx_source import PytdxDataSource
from etf_analyzer.data_sources.tushare_source import TushareDataSource
from etf_analyzer.utils.logger import setup_logger

# 数据源名称到类的映射，用于 register_all 自动实例化
_SOURCE_CLASS_MAP = {
    "akshare": AkshareDataSource,
    "tushare": TushareDataSource,
    "baostock": BaostockDataSource,
    "pytdx": PytdxDataSource,
}


class DataSourceManager:
    """数据源管理器，负责多数据源的注册、优先级排序、健康检查和自动故障转移。

    通过统一的 fetch 接口按优先级依次尝试各数据源，某数据源失败时自动切换
    到下一个，所有数据源均失败时返回空数据。健康检查结果会缓存，避免频繁检查。

    Attributes:
        logger: 日志记录器实例。
    """

    def __init__(self):
        """初始化 DataSourceManager 实例。"""
        self.logger = setup_logger("data_source_manager")
        self._sources = []  # 按优先级排列的数据源列表
        self._source_map = {}  # 名称到数据源实例的映射
        self._health_status = {}  # 名称到健康检查结果的映射
        self._last_health_check_time = 0.0  # 上次健康检查的时间戳
        self._lock = threading.Lock()

    def register(self, source: BaseDataSource):
        """注册数据源。

        将数据源添加到管理器中，如果同名数据源已存在则跳过。
        注册后按配置的优先级重新排序。

        Args:
            source: 数据源实例，必须实现 BaseDataSource 接口。
        """
        with self._lock:
            if source.name in self._source_map:
                self.logger.warning("数据源 '%s' 已注册，跳过重复注册", source.name)
                return
            self._source_map[source.name] = source
            self._sources.append(source)
            # 按配置优先级排序
            self._sort_sources()
            self.logger.info(
                "已注册数据源 '%s'，当前数据源顺序: %s",
                source.name, [s.name for s in self._sources],
            )

    def register_all(self):
        """自动注册所有可用数据源。

        从 config.DATASOURCE_PRIORITY 读取优先级列表，依次实例化对应的数据源类
        并注册。仅注册 available 属性为 True 的数据源。
        """
        registered = []
        skipped = []
        for name in DATASOURCE_PRIORITY:
            cls = _SOURCE_CLASS_MAP.get(name)
            if cls is None:
                self.logger.warning("未知数据源名称: '%s'，跳过", name)
                skipped.append(name)
                continue
            try:
                source = cls()
                if source.available:
                    self.register(source)
                    registered.append(name)
                else:
                    self.logger.info("数据源 '%s' 不可用，跳过注册", name)
                    skipped.append(name)
            except Exception as e:
                self.logger.error("实例化数据源 '%s' 失败: %s", name, e)
                skipped.append(name)

        self.logger.info(
            "数据源自动注册完成，已注册: %s，跳过: %s",
            registered, skipped,
        )

    def _sort_sources(self):
        """按配置优先级对数据源列表排序。

        在 DATASOURCE_PRIORITY 中排在前面的数据源优先级更高。
        不在配置列表中的数据源排到末尾。
        """
        def priority_key(source):
            try:
                return DATASOURCE_PRIORITY.index(source.name)
            except ValueError:
                return len(DATASOURCE_PRIORITY)

        self._sources.sort(key=priority_key)

    def health_check_all(self):
        """对所有注册的数据源执行健康检查。

        记录每个数据源的响应时间和可用状态，检查结果缓存到 _health_status 中。
        健康检查间隔由 config.DATASOURCE_HEALTH_CHECK_INTERVAL 控制（默认300秒），
        未超过间隔则跳过检查。
        检查完成后，不可用的数据源会被排到末尾，但仍保留在列表中。
        """
        now = time.time()
        # 检查是否在缓存间隔内
        if (now - self._last_health_check_time) < DATASOURCE_HEALTH_CHECK_INTERVAL:
            self.logger.debug("健康检查间隔未到，跳过本次检查")
            return

        self.logger.info("开始执行数据源健康检查...")
        unavailable_names = []

        for source in self._sources:
            try:
                result = source.health_check()
                self._health_status[source.name] = result
                if result["available"]:
                    self.logger.info(
                        "数据源 '%s' 健康，响应时间: %s 秒",
                        source.name, result["response_time"],
                    )
                else:
                    self.logger.warning(
                        "数据源 '%s' 不可用: %s",
                        source.name, result.get("error", "未知错误"),
                    )
                    unavailable_names.append(source.name)
            except Exception as e:
                self.logger.error(
                    "数据源 '%s' 健康检查异常: %s", source.name, e,
                )
                self._health_status[source.name] = {
                    "name": source.name,
                    "available": False,
                    "response_time": None,
                    "error": str(e),
                }
                unavailable_names.append(source.name)

        self._last_health_check_time = time.time()

        # 动态调整优先级：不可用的数据源排到末尾
        if unavailable_names:
            with self._lock:
                available_sources = [
                    s for s in self._sources if s.name not in unavailable_names
                ]
                unavailable_sources = [
                    s for s in self._sources if s.name in unavailable_names
                ]
                self._sources = available_sources + unavailable_sources
                self.logger.info(
                    "健康检查后数据源顺序: %s",
                    [s.name for s in self._sources],
                )

        self.logger.info("数据源健康检查完成")

    def fetch(self, method_name: str, **kwargs):
        """统一获取方法，按优先级依次尝试各数据源。

        先执行健康检查（如果缓存过期），然后按当前优先级顺序依次调用
        各数据源的指定方法。某数据源失败时记录 WARNING 日志并切换到下一个，
        所有数据源均失败时记录 ERROR 日志并返回空数据。

        Args:
            method_name: 要调用的数据源方法名，如 "get_realtime_quote"。
            **kwargs: 传递给数据源方法的参数。

        Returns:
            第一个成功的数据源返回的结果。
            所有数据源均失败时返回空字典 {} 或空 DataFrame，取决于方法类型。
        """
        # 触发健康检查（如果缓存过期）
        self.health_check_all()

        # 获取当前数据源列表的快照（避免迭代中列表被修改）
        with self._lock:
            sources_snapshot = list(self._sources)

        for source in sources_snapshot:
            # 跳过健康检查标记为不可用的数据源
            health = self._health_status.get(source.name)
            if health and not health.get("available", True):
                self.logger.debug(
                    "跳过不可用的数据源 '%s'", source.name,
                )
                continue

            # 检查数据源是否支持该方法
            method = getattr(source, method_name, None)
            if method is None or not callable(method):
                self.logger.debug(
                    "数据源 '%s' 不支持方法 '%s'", source.name, method_name,
                )
                continue

            try:
                result = method(**kwargs)
                # 检查结果是否为空
                if self._is_empty_result(result):
                    self.logger.warning(
                        "数据源 '%s' 的方法 '%s' 返回空数据，尝试下一个数据源",
                        source.name, method_name,
                    )
                    continue
                self.logger.info(
                    "通过数据源 '%s' 成功获取数据（方法: %s）",
                    source.name, method_name,
                )
                return result
            except Exception as e:
                self.logger.warning(
                    "数据源 '%s' 的方法 '%s' 调用失败: %s，尝试下一个数据源",
                    source.name, method_name, e,
                )
                # 标记该数据源为不可用
                self._health_status[source.name] = {
                    "name": source.name,
                    "available": False,
                    "response_time": None,
                    "error": str(e),
                }
                continue

        # 所有数据源均失败
        self.logger.error(
            "所有数据源均无法获取数据（方法: %s，参数: %s）",
            method_name, kwargs,
        )
        return self._empty_result_for_method(method_name)

    @staticmethod
    def _is_empty_result(result):
        """检查数据源返回结果是否为空。

        Args:
            result: 数据源方法的返回值。

        Returns:
            bool: 结果为空返回 True，否则返回 False。
        """
        if result is None:
            return True
        if isinstance(result, dict) and len(result) == 0:
            return True
        if isinstance(result, pd.DataFrame) and result.empty:
            return True
        return False

    @staticmethod
    def _empty_result_for_method(method_name: str):
        """根据方法名返回对应的空结果。

        Args:
            method_name: 数据源方法名。

        Returns:
            空字典或空 DataFrame，取决于方法类型。
        """
        if method_name == "get_realtime_quote":
            return {}
        return pd.DataFrame()

    def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情，委托给 fetch。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            dict: 实时行情数据，失败返回空字典。
        """
        return self.fetch("get_realtime_quote", symbol=symbol)

    def get_history_data(self, symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取历史数据，委托给 fetch。

        Args:
            symbol: ETF代码，如 "510300"。
            start_date: 起始日期，格式 YYYYMMDD。
            end_date: 结束日期，格式 YYYYMMDD。
            adjust: 复权类型，"qfq"/"hfq"/""，默认 "qfq"。

        Returns:
            DataFrame: 历史行情数据，失败返回空 DataFrame。
        """
        return self.fetch(
            "get_history_data",
            symbol=symbol, start_date=start_date, end_date=end_date, adjust=adjust,
        )

    def get_etf_list(self, keyword: str = None) -> pd.DataFrame:
        """获取ETF列表，委托给 fetch。

        Args:
            keyword: 可选过滤关键词。

        Returns:
            DataFrame: ETF列表数据，失败返回空 DataFrame。
        """
        return self.fetch("get_etf_list", keyword=keyword)

    def get_etf_holdings(self, symbol: str) -> pd.DataFrame:
        """获取ETF持仓信息，委托给 fetch。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            DataFrame: 持仓信息数据，失败返回空 DataFrame。
        """
        return self.fetch("get_etf_holdings", symbol=symbol)

    def get_source_status(self) -> list:
        """返回各数据源的健康状态列表。

        Returns:
            list: 健康状态字典列表，每个字典包含：
                name: 数据源名称
                available: 是否可用
                response_time: 响应时间（秒），不可用时为 None
                error: 错误信息，正常时为 None
        """
        status_list = []
        for source in self._sources:
            health = self._health_status.get(source.name)
            if health:
                status_list.append(health)
            else:
                status_list.append({
                    "name": source.name,
                    "available": source.available,
                    "response_time": None,
                    "error": None,
                })
        return status_list
