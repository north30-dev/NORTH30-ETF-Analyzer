# -*- coding: utf-8 -*-
"""
ETF分析器统一日志记录模块

本模块提供了统一的日志记录功能，支持同时输出到控制台和文件，
并使用 RotatingFileHandler 控制日志文件大小，防止单个日志文件过大。
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

from config import LOG_DIR_PATH, LOG_LEVEL, LOG_FORMAT, ensure_dirs


def setup_logger(name="etf_analyzer", level=None):
    """创建并配置日志记录器。

    根据指定的名称和日志级别创建 logger 实例，同时配置控制台输出
    和文件输出两个 handler。日志文件按日期命名，存放在日志目录下，
    并使用 RotatingFileHandler 控制单个日志文件的大小。

    Args:
        name (str): 日志记录器的名称，默认为 "etf_analyzer"。
                    建议使用模块名作为 name，便于追踪日志来源。
        level (str): 日志级别，可选值为 "DEBUG"、"INFO"、"WARNING"、
                     "ERROR"、"CRITICAL"。默认为 None，表示使用
                     config.py 中定义的全局日志级别 LOG_LEVEL。

    Returns:
        logging.Logger: 配置好的日志记录器实例。

    Example:
        >>> logger = setup_logger("data_fetcher")
        >>> logger.info("开始获取ETF数据")
        >>> logger.error("数据获取失败: %s", "网络超时")
    """
    # 确保日志目录存在
    ensure_dirs()

    # 确定日志级别
    if level is None:
        level = LOG_LEVEL
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 创建 logger 实例
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 避免重复添加 handler（防止多次调用 setup_logger 导致重复日志）
    if logger.handlers:
        return logger

    # 创建日志格式器
    formatter = logging.Formatter(LOG_FORMAT)

    # ---- 控制台输出 handler ----
    # 显式指定 UTF-8 编码，避免 Windows 终端中文乱码
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    # 确保 StreamHandler 使用 UTF-8 编码输出
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8')
    logger.addHandler(console_handler)

    # ---- 文件输出 handler ----
    # 日志文件按日期命名，格式：etf_analyzer_YYYYMMDD.log
    log_filename = f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(LOG_DIR_PATH, log_filename)

    # 使用 RotatingFileHandler 控制日志文件大小
    # 单文件最大 10MB，保留 3 个备份文件
    file_handler = RotatingFileHandler(
        log_filepath,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
