# -*- coding: utf-8 -*-
"""
数据源抽象层包

提供统一的数据源接口（BaseDataSource）及其具体实现，
支持多种数据源的灵活切换与扩展。
"""

from etf_analyzer.data_sources.base import BaseDataSource
from etf_analyzer.data_sources.akshare_source import AkshareDataSource
from etf_analyzer.data_sources.baostock_source import BaostockDataSource
from etf_analyzer.data_sources.pytdx_source import PytdxDataSource
from etf_analyzer.data_sources.tushare_source import TushareDataSource

__all__ = ["BaseDataSource", "AkshareDataSource", "BaostockDataSource", "PytdxDataSource", "TushareDataSource"]
