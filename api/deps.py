# -*- coding: utf-8 -*-
"""API 依赖注入"""

from functools import lru_cache

from etf_analyzer.core.data_fetcher import ETFDataFetcher
from etf_analyzer.core.analyzer import ETFAnalyzer
from etf_analyzer.core.visualizer import ETFVisualizer
from etf_analyzer.core.report_generator import ReportGenerator
from etf_analyzer.core.data_processor import DataProcessor


@lru_cache()
def get_fetcher() -> ETFDataFetcher:
    """获取 ETFDataFetcher 实例（单例）。"""
    return ETFDataFetcher()


@lru_cache()
def get_analyzer() -> ETFAnalyzer:
    """获取 ETFAnalyzer 实例（单例）。"""
    return ETFAnalyzer()


@lru_cache()
def get_visualizer() -> ETFVisualizer:
    """获取 ETFVisualizer 实例（单例）。"""
    return ETFVisualizer()


@lru_cache()
def get_report_generator() -> ReportGenerator:
    """获取 ReportGenerator 实例（单例）。"""
    return ReportGenerator()


@lru_cache()
def get_processor() -> DataProcessor:
    """获取 DataProcessor 实例（单例）。"""
    return DataProcessor()
