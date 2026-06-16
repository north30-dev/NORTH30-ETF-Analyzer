# -*- coding: utf-8 -*-
"""
ETF增量更新模块

本模块实现ETF数据的增量更新、定时任务调度和数据版本管理功能，
支持历史数据和持仓数据的增量同步，避免重复获取已有数据。
"""

import json
import os
import threading
from datetime import datetime, timedelta

import pandas as pd

from config import CACHE_DIR_PATH, DEFAULT_START_DATE, ensure_dirs
from etf_analyzer.utils.logger import setup_logger


class IncrementalUpdater:
    """ETF增量更新器，支持增量数据同步、定时任务和数据版本管理。

    通过记录每次更新的版本信息，实现增量获取数据，避免重复请求。
    支持定时调度自动更新，使用 threading.Timer 实现轻量级调度。

    Attributes:
        logger: 日志记录器实例。
        fetcher: ETFDataFetcher 数据获取器实例。
        version_dir: 版本信息文件存储目录。
    """

    def __init__(self, fetcher=None):
        """初始化IncrementalUpdater实例。

        Args:
            fetcher (ETFDataFetcher, optional): 数据获取器实例。
                如果未提供则自动创建。
        """
        self.logger = setup_logger("incremental_updater")

        if fetcher is None:
            from etf_analyzer.core.data_fetcher import ETFDataFetcher
            self.fetcher = ETFDataFetcher()
        else:
            self.fetcher = fetcher

        # 初始化版本信息存储目录
        self.version_dir = os.path.join(CACHE_DIR_PATH, "data_versions")
        os.makedirs(self.version_dir, exist_ok=True)

        # 定时调度相关属性
        self._schedule_config = None
        self._scheduler_timer = None
        self._scheduler_running = False

        self.logger.info("IncrementalUpdater 初始化完成，版本目录: %s", self.version_dir)

    # ================================================================
    # SubTask 6.1: 增量数据同步
    # ================================================================

    def get_last_update_date(self, symbol, data_type="history"):
        """获取上次更新日期。

        从版本信息文件中读取上次更新日期。

        Args:
            symbol (str): ETF代码，如 "510300"。
            data_type (str): 数据类型，默认为 "history"。

        Returns:
            str or None: 上次更新日期字符串（YYYYMMDD格式），
                如果没有版本信息返回 None。
        """
        version = self._load_version(symbol, data_type)
        if version is None:
            self.logger.info(
                "未找到 %s 的 %s 版本信息", symbol, data_type,
            )
            return None

        last_date = version.get("last_date")
        self.logger.info(
            "%s 的 %s 上次更新日期: %s", symbol, data_type, last_date,
        )
        return last_date

    def incremental_update(self, symbol, start_date=None, end_date=None, adjust="qfq"):
        """增量更新历史数据。

        仅获取增量数据，与已有缓存数据合并，并更新版本信息。

        Args:
            symbol (str): ETF代码，如 "510300"。
            start_date (str, optional): 起始日期，格式 YYYYMMDD。
                如果未提供，则从上次更新日期的下一天开始。
                如果没有上次更新记录，则使用 config.DEFAULT_START_DATE。
            end_date (str, optional): 结束日期，格式 YYYYMMDD。
                默认使用当天日期。
            adjust (str): 复权类型，默认为 "qfq"。

        Returns:
            pandas.DataFrame: 合并后的完整历史数据 DataFrame。
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # 确定增量更新的起始日期
        if start_date is None:
            last_date = self.get_last_update_date(symbol, "history")
            if last_date is not None:
                # 从上次更新日期的下一天开始
                next_day = (
                    datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)
                ).strftime("%Y%m%d")
                start_date = next_day
                self.logger.info(
                    "增量更新 %s 历史数据，从上次更新日期下一天开始: %s",
                    symbol, start_date,
                )
            else:
                start_date = DEFAULT_START_DATE
                self.logger.info(
                    "无上次更新记录，使用默认起始日期: %s", start_date,
                )

        # 如果起始日期已经超过结束日期，无需更新
        if start_date > end_date:
            self.logger.info(
                "起始日期 %s 超过结束日期 %s，无需增量更新 %s",
                start_date, end_date, symbol,
            )
            # 返回已有的缓存数据
            existing_data = self._load_cached_history(symbol, adjust)
            return existing_data if existing_data is not None else pd.DataFrame()

        # 获取增量数据
        self.logger.info(
            "开始增量更新 %s 历史数据，起始: %s，结束: %s",
            symbol, start_date, end_date,
        )
        incremental_df = self.fetcher.get_history_data(
            symbol, start_date=start_date, end_date=end_date, adjust=adjust,
        )

        # 加载已有缓存数据
        existing_data = self._load_cached_history(symbol, adjust)

        # 合并数据
        if existing_data is not None and not existing_data.empty:
            merged_df = self._merge_history_data(existing_data, incremental_df)
            self.logger.info(
                "合并 %s 历史数据，已有 %d 条，增量 %d 条，合并后 %d 条",
                symbol, len(existing_data), len(incremental_df), len(merged_df),
            )
        else:
            merged_df = incremental_df
            self.logger.info(
                "无已有数据，使用增量数据 %d 条作为完整数据", len(merged_df),
            )

        # 更新版本信息
        if not merged_df.empty:
            last_date = self._get_last_date_from_df(merged_df)
            self._save_version(
                symbol, "history",
                record_count=len(merged_df),
                source_name="incremental_update",
                last_date=last_date,
            )

        return merged_df

    def incremental_update_holdings(self, symbol):
        """增量更新持仓数据。

        持仓数据按年更新，检查是否已有当年数据。

        Args:
            symbol (str): ETF代码，如 "510300"。

        Returns:
            pandas.DataFrame: 最新持仓数据 DataFrame。
        """
        current_year = str(datetime.now().year)
        self.logger.info(
            "检查 %s 持仓数据更新，当前年份: %s", symbol, current_year,
        )

        # 检查是否已有当年版本信息
        version = self._load_version(symbol, "holdings")
        if version is not None and version.get("last_date") == current_year:
            self.logger.info(
                "%s 持仓数据已是 %s 年最新，无需更新", symbol, current_year,
            )
            # 返回缓存的持仓数据
            cached = self.fetcher.get_etf_holdings(symbol)
            return cached

        # 获取最新持仓数据
        self.logger.info("开始增量更新 %s 持仓数据", symbol)
        holdings_df = self.fetcher.get_etf_holdings(symbol)

        # 更新版本信息
        if not holdings_df.empty:
            self._save_version(
                symbol, "holdings",
                record_count=len(holdings_df),
                source_name="incremental_update",
                last_date=current_year,
            )

        return holdings_df

    # ================================================================
    # SubTask 6.2: 定时任务自动更新
    # ================================================================

    def schedule_update(self, symbols, update_time="16:00", weekdays=None):
        """配置定时更新计划。

        Args:
            symbols (list): 需要更新的 ETF 代码列表。
            update_time (str): 每日更新时间，格式 "HH:MM"，默认 "16:00"。
            weekdays (list, optional): 星期几更新（1-5对应周一到周五），
                默认 [1, 2, 3, 4, 5]。
        """
        if weekdays is None:
            weekdays = [1, 2, 3, 4, 5]

        self._schedule_config = {
            "symbols": symbols,
            "update_time": update_time,
            "weekdays": weekdays,
        }

        # 保存更新计划到配置文件
        config_path = os.path.join(self.version_dir, "schedule_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._schedule_config, f, ensure_ascii=False, indent=2)
            self.logger.info(
                "定时更新计划已保存，ETF列表: %s，更新时间: %s，星期: %s",
                symbols, update_time, weekdays,
            )
        except Exception as e:
            self.logger.error("保存定时更新计划失败: %s", e)

    def run_scheduled_update(self):
        """执行定时更新。

        检查当前时间是否到达更新时间，对计划中的所有 ETF 执行增量更新，
        记录更新结果日志。

        Returns:
            dict: 更新结果摘要，包含每个 ETF 的更新状态。
        """
        if self._schedule_config is None:
            # 尝试从配置文件加载
            config_path = os.path.join(self.version_dir, "schedule_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        self._schedule_config = json.load(f)
                except Exception as e:
                    self.logger.error("加载定时更新计划失败: %s", e)
                    return {}

            if self._schedule_config is None:
                self.logger.warning("未配置定时更新计划")
                return {}

        symbols = self._schedule_config.get("symbols", [])
        update_time = self._schedule_config.get("update_time", "16:00")
        weekdays = self._schedule_config.get("weekdays", [1, 2, 3, 4, 5])

        # 检查当前是否为允许更新的星期
        current_weekday = datetime.now().isoweekday()
        if current_weekday not in weekdays:
            self.logger.info(
                "当前星期 %d 不在更新计划中（%s），跳过更新",
                current_weekday, weekdays,
            )
            return {}

        # 检查当前时间是否到达更新时间
        now = datetime.now()
        target_hour, target_minute = map(int, update_time.split(":"))
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if now < target_time:
            self.logger.info(
                "当前时间 %s 未到达更新时间 %s，跳过更新",
                now.strftime("%H:%M:%S"), update_time,
            )
            return {}

        # 执行增量更新
        results = {}
        for symbol in symbols:
            try:
                self.logger.info("开始定时更新 ETF: %s", symbol)
                # 更新历史数据
                history_df = self.incremental_update(symbol)
                # 更新持仓数据
                holdings_df = self.incremental_update_holdings(symbol)

                results[symbol] = {
                    "status": "success",
                    "history_records": len(history_df),
                    "holdings_records": len(holdings_df),
                    "update_time": now.isoformat(),
                }
                self.logger.info(
                    "ETF %s 更新成功，历史数据 %d 条，持仓数据 %d 条",
                    symbol, len(history_df), len(holdings_df),
                )
            except Exception as e:
                results[symbol] = {
                    "status": "failed",
                    "error": str(e),
                    "update_time": now.isoformat(),
                }
                self.logger.error("ETF %s 更新失败: %s", symbol, e)

        self.logger.info("定时更新完成，结果: %s", results)
        return results

    def start_scheduler(self, blocking=False):
        """启动定时调度器。

        使用 threading.Timer 实现简单的定时调度。

        Args:
            blocking (bool): 是否阻塞主线程。
                False 时在后台线程运行，True 时阻塞主线程。
        """
        if self._schedule_config is None:
            # 尝试从配置文件加载
            config_path = os.path.join(self.version_dir, "schedule_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        self._schedule_config = json.load(f)
                except Exception as e:
                    self.logger.error("加载定时更新计划失败: %s", e)

            if self._schedule_config is None:
                self.logger.warning("未配置定时更新计划，无法启动调度器")
                return

        self._scheduler_running = True
        self.logger.info(
            "定时调度器启动，模式: %s",
            "阻塞" if blocking else "后台",
        )

        if blocking:
            self._scheduler_loop()
        else:
            scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True,
            )
            scheduler_thread.start()

    def stop_scheduler(self):
        """停止定时调度器。"""
        self._scheduler_running = False
        if self._scheduler_timer is not None:
            self._scheduler_timer.cancel()
            self._scheduler_timer = None
        self.logger.info("定时调度器已停止")

    def _scheduler_loop(self):
        """调度器主循环，每分钟检查一次是否到达更新时间。"""
        while self._scheduler_running:
            now = datetime.now()
            # 计算到下一分钟的等待时间
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            wait_seconds = (next_minute - now).total_seconds()

            # 使用 Timer 等待
            self._scheduler_timer = threading.Timer(wait_seconds, self._check_and_run)
            self._scheduler_timer.start()
            self._scheduler_timer.join()

            if not self._scheduler_running:
                break

    def _check_and_run(self):
        """检查并执行定时更新（由调度器内部调用）。"""
        if not self._scheduler_running:
            return

        if self._schedule_config is None:
            return

        update_time = self._schedule_config.get("update_time", "16:00")
        weekdays = self._schedule_config.get("weekdays", [1, 2, 3, 4, 5])

        now = datetime.now()

        # 检查星期
        if now.isoweekday() not in weekdays:
            return

        # 检查是否到达更新时间（精确到分钟）
        target_hour, target_minute = map(int, update_time.split(":"))
        if now.hour == target_hour and now.minute == target_minute:
            self.logger.info("到达定时更新时间，开始执行更新")
            self.run_scheduled_update()

    # ================================================================
    # SubTask 6.3: 数据版本管理
    # ================================================================

    def _save_version(self, symbol, data_type, record_count, source_name, last_date=None):
        """保存版本信息。

        Args:
            symbol (str): ETF代码。
            data_type (str): 数据类型，如 "history"、"holdings"。
            record_count (int): 记录数。
            source_name (str): 数据来源标识。
            last_date (str, optional): 数据最后日期（YYYYMMDD格式）。
        """
        version_info = {
            "symbol": symbol,
            "data_type": data_type,
            "last_update": datetime.now().isoformat(),
            "last_date": last_date,
            "record_count": record_count,
            "source": source_name,
        }

        version_path = os.path.join(
            self.version_dir, f"{symbol}_{data_type}_version.json",
        )

        try:
            os.makedirs(os.path.dirname(version_path), exist_ok=True)
            with open(version_path, "w", encoding="utf-8") as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)
            self.logger.info(
                "版本信息已保存: %s，记录数: %d，最后日期: %s",
                version_path, record_count, last_date,
            )
        except Exception as e:
            self.logger.error("保存版本信息失败: %s", e)

    def _load_version(self, symbol, data_type):
        """加载版本信息。

        Args:
            symbol (str): ETF代码。
            data_type (str): 数据类型，如 "history"、"holdings"。

        Returns:
            dict or None: 版本信息字典，如果文件不存在返回 None。
        """
        version_path = os.path.join(
            self.version_dir, f"{symbol}_{data_type}_version.json",
        )

        if not os.path.exists(version_path):
            return None

        try:
            with open(version_path, "r", encoding="utf-8") as f:
                version_info = json.load(f)
            self.logger.debug("加载版本信息: %s", version_path)
            return version_info
        except Exception as e:
            self.logger.error("加载版本信息失败: %s，异常: %s", version_path, e)
            return None

    def get_version_history(self, symbol, data_type="history"):
        """获取版本历史摘要。

        Args:
            symbol (str): ETF代码。
            data_type (str): 数据类型，默认为 "history"。

        Returns:
            dict or None: 当前版本信息字典。
        """
        version = self._load_version(symbol, data_type)
        if version is not None:
            self.logger.info(
                "%s 的 %s 版本信息: 最后更新 %s，记录数 %d",
                symbol, data_type,
                version.get("last_update", "未知"),
                version.get("record_count", 0),
            )
        else:
            self.logger.info("未找到 %s 的 %s 版本信息", symbol, data_type)
        return version

    # ================================================================
    # 辅助方法
    # ================================================================

    def _load_cached_history(self, symbol, adjust="qfq"):
        """加载缓存的历史数据。

        尝试从 fetcher 的缓存目录加载已有的历史数据。

        Args:
            symbol (str): ETF代码。
            adjust (str): 复权类型。

        Returns:
            pandas.DataFrame or None: 缓存的历史数据，不存在则返回 None。
        """
        # 遍历缓存目录查找匹配的历史数据文件
        cache_dir = self.fetcher.cache_dir
        if not os.path.exists(cache_dir):
            return None

        # 查找与该 symbol 和 adjust 相关的缓存文件
        matching_files = []
        for filename in os.listdir(cache_dir):
            if filename.startswith(symbol) and "history" in filename and adjust in filename:
                filepath = os.path.join(cache_dir, filename)
                matching_files.append(filepath)

        if not matching_files:
            return None

        # 选择最新的缓存文件
        matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        latest_file = matching_files[0]

        try:
            import pickle
            with open(latest_file, "rb") as f:
                data = pickle.load(f)
            self.logger.info("加载缓存历史数据: %s", latest_file)
            return data
        except Exception as e:
            self.logger.warning("加载缓存历史数据失败: %s，异常: %s", latest_file, e)
            return None

    def _merge_history_data(self, existing_df, incremental_df):
        """合并已有历史数据和增量数据。

        去重并按日期排序，确保数据完整性。

        Args:
            existing_df (pandas.DataFrame): 已有历史数据。
            incremental_df (pandas.DataFrame): 增量数据。

        Returns:
            pandas.DataFrame: 合并后的完整历史数据。
        """
        if incremental_df.empty:
            return existing_df

        if existing_df.empty:
            return incremental_df

        # 合并数据
        merged_df = pd.concat([existing_df, incremental_df], ignore_index=True)

        # 尝试按日期列去重
        date_col = None
        for col_name in ["日期", "date", "trade_date"]:
            if col_name in merged_df.columns:
                date_col = col_name
                break

        if date_col is not None:
            # 保留增量数据（后出现的），去重
            merged_df = merged_df.drop_duplicates(subset=[date_col], keep="last")
            # 按日期排序
            merged_df = merged_df.sort_values(by=date_col).reset_index(drop=True)
        else:
            # 无日期列，简单去重
            merged_df = merged_df.drop_duplicates().reset_index(drop=True)

        return merged_df

    def _get_last_date_from_df(self, df):
        """从 DataFrame 中获取最后日期。

        Args:
            df (pandas.DataFrame): 历史数据 DataFrame。

        Returns:
            str or None: 最后日期字符串（YYYYMMDD格式），无法获取则返回 None。
        """
        if df.empty:
            return None

        # 查找日期列
        date_col = None
        for col_name in ["日期", "date", "trade_date"]:
            if col_name in df.columns:
                date_col = col_name
                break

        if date_col is None:
            return None

        try:
            last_val = df[date_col].iloc[-1]
            # 尝试转换为 YYYYMMDD 格式
            if isinstance(last_val, str):
                # 尝试解析并格式化
                try:
                    parsed = pd.to_datetime(last_val)
                    return parsed.strftime("%Y%m%d")
                except Exception:
                    return last_val
            else:
                # datetime 或 Timestamp 类型
                parsed = pd.to_datetime(last_val)
                return parsed.strftime("%Y%m%d")
        except Exception as e:
            self.logger.warning("获取最后日期失败: %s", e)
            return None
