# -*- coding: utf-8 -*-
"""
ETF 分析工具包

提供快捷导入，保持向后兼容。
使用 lazy import 避免循环依赖。
"""


def __getattr__(name):
    """延迟导入，避免循环依赖。"""
    _lazy_imports = {
        # 核心模块
        "ETFAnalyzer": "etf_analyzer.core.analyzer",
        "ETFDataFetcher": "etf_analyzer.core.data_fetcher",
        "DataProcessor": "etf_analyzer.core.data_processor",
        "ETFVisualizer": "etf_analyzer.core.visualizer",
        "ReportGenerator": "etf_analyzer.core.report_generator",
        "AVAILABLE_MODULES": "etf_analyzer.core.report_generator",
        # 服务模块
        "DataSourceManager": "etf_analyzer.services.data_source_manager",
        "DataCompletion": "etf_analyzer.services.data_completion",
        "IncrementalUpdater": "etf_analyzer.services.incremental_updater",
        "DataMonitor": "etf_analyzer.services.data_monitor",
        # 工具模块
        "setup_logger": "etf_analyzer.utils.logger",
        "retry": "etf_analyzer.utils.retry",
        "rate_limiter": "etf_analyzer.utils.retry",
        "SecureConfig": "etf_analyzer.utils.secure_config",
        "secure_config": "etf_analyzer.utils.secure_config",
    }
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
