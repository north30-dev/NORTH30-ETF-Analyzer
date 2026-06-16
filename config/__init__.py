# -*- coding: utf-8 -*-
"""
统一配置管理包

提供全局配置单例访问接口，以及向后兼容的模块级常量。
"""

from config.settings import Settings, get_settings, reset_settings, PROJECT_ROOT

# 获取全局配置单例，用于导出向后兼容的常量
_settings = get_settings()

# ============================================================
# 向后兼容常量（原 etf_analyzer.config 导出）
# ============================================================

# 路径常量（转为字符串以保持与旧版 os.path.join 结果一致）
CACHE_DIR_PATH = str(_settings.cache_dir_path)
LOG_DIR_PATH = str(_settings.log_dir_path)
REPORT_DIR_PATH = str(_settings.report_dir_path)

# 缓存配置
CACHE_EXPIRE_HOURS = _settings.cache.expire_hours

# 日志配置
LOG_LEVEL = _settings.logging.level
LOG_FORMAT = _settings.logging.format

# 分析参数
DEFAULT_START_DATE = _settings.analysis.default_start_date
RISK_FREE_RATE = _settings.analysis.risk_free_rate

# 行业分类映射
SW_INDUSTRY_MAP = _settings.sw_industry_map
ZX_INDUSTRY_MAP = _settings.zx_industry_map

# 报告配置
REPORT_FONT = _settings.report.font
REPORT_FONT_SIZE = _settings.report.font_size
REPORT_TITLE_FONT_SIZE = _settings.report.title_font_size

# 数据源配置
DATASOURCE_PRIORITY = _settings.datasource.priority
DATASOURCE_HEALTH_CHECK_INTERVAL = _settings.datasource.health_check_interval
DATASOURCE_FAILURE_THRESHOLD = _settings.datasource.failure_threshold
DATA_QUALITY_THRESHOLD = _settings.datasource.quality_threshold
CROSS_VALIDATION_THRESHOLD = _settings.datasource.cross_validation_threshold
TUSHARE_TOKEN = _settings.datasource.tushare_token
PYTDX_HOST = _settings.datasource.pytdx_host
PYTDX_PORT = _settings.datasource.pytdx_port


def ensure_dirs():
    """确保所有必要的目录存在。"""
    _settings.ensure_dirs()


__all__ = [
    # 新配置系统
    "Settings", "get_settings", "reset_settings", "PROJECT_ROOT",
    # 路径常量
    "CACHE_DIR_PATH", "LOG_DIR_PATH", "REPORT_DIR_PATH",
    # 缓存配置
    "CACHE_EXPIRE_HOURS",
    # 日志配置
    "LOG_LEVEL", "LOG_FORMAT",
    # 分析参数
    "DEFAULT_START_DATE", "RISK_FREE_RATE",
    # 行业分类映射
    "SW_INDUSTRY_MAP", "ZX_INDUSTRY_MAP",
    # 报告配置
    "REPORT_FONT", "REPORT_FONT_SIZE", "REPORT_TITLE_FONT_SIZE",
    # 数据源配置
    "DATASOURCE_PRIORITY", "DATASOURCE_HEALTH_CHECK_INTERVAL",
    "DATASOURCE_FAILURE_THRESHOLD", "DATA_QUALITY_THRESHOLD",
    "CROSS_VALIDATION_THRESHOLD", "TUSHARE_TOKEN",
    "PYTDX_HOST", "PYTDX_PORT",
    # 工具函数
    "ensure_dirs",
]
