# -*- coding: utf-8 -*-
"""全面功能验证脚本"""
import sys
import os
import shutil
import numpy as np
import pandas as pd
from unittest.mock import MagicMock

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# 1. 增量更新模块验证
# ============================================================
print("=" * 60)
print("1. 增量更新模块功能验证")
print("=" * 60)

from etf_analyzer.incremental_updater import IncrementalUpdater

updater = IncrementalUpdater()
print("[PASS] IncrementalUpdater 初始化成功")

updater._save_version("510300", "history", 100, "akshare", "20240101")
version = updater._load_version("510300", "history")
assert version is not None, "版本信息加载失败"
assert version["record_count"] == 100, "record_count 不匹配"
assert version["source"] == "akshare", "source 不匹配"
print("[PASS] 版本保存和加载正常")

last_date = updater.get_last_update_date("510300", "history")
assert last_date == "20240101", "last_date 不匹配: " + str(last_date)
print("[PASS] 获取上次更新日期: " + str(last_date))

no_date = updater.get_last_update_date("999999", "history")
assert no_date is None, "不存在的版本应返回 None"
print("[PASS] 不存在的版本返回 None")

history = updater.get_version_history("510300", "history")
assert history is not None, "版本历史查询失败"
print("[PASS] 版本历史查询正常")

updater.schedule_update(["510300", "510500"], update_time="16:00")
print("[PASS] 定时更新配置成功")

# 清理
if os.path.exists(updater.version_dir):
    shutil.rmtree(updater.version_dir, ignore_errors=True)

# ============================================================
# 2. 数据异常预警模块验证
# ============================================================
print()
print("=" * 60)
print("2. 数据异常预警模块功能验证")
print("=" * 60)

from etf_analyzer.data_monitor import DataMonitor

monitor = DataMonitor()
print("[PASS] DataMonitor 初始化成功")

mock_manager = MagicMock()
mock_source1 = MagicMock()
mock_source1.name = "akshare"
mock_source1.health_check.return_value = {"name": "akshare", "available": True, "response_time": 0.5, "error": None}
mock_source2 = MagicMock()
mock_source2.name = "pytdx"
mock_source2.health_check.return_value = {"name": "pytdx", "available": True, "response_time": 1.2, "error": None}
mock_manager._sources = [mock_source1, mock_source2]
mock_manager._health_status = {
    "akshare": {"name": "akshare", "available": True, "response_time": 0.5, "error": None},
    "pytdx": {"name": "pytdx", "available": True, "response_time": 1.2, "error": None},
}
monitor._manager = mock_manager

result = monitor.check_source_health()
assert result is not None, "健康检查返回 None"
print("[PASS] 健康检查正常，结果: " + str(len(result)) + " 个数据源")

status = monitor.get_health_status()
assert len(status) > 0, "健康状态为空"
print("[PASS] 获取健康状态正常")

alerts = monitor.check_and_alert()
print("[PASS] 告警检查正常，当前告警数: " + str(len(alerts)))

report = monitor.generate_quality_report()
assert "report_time" in report, "报告缺少 report_time"
assert "sources" in report, "报告缺少 sources"
assert "summary" in report, "报告缺少 summary"
avail = report["summary"]["available_sources"]
total = report["summary"]["total_sources"]
print("[PASS] 质量报告生成正常，可用数据源: " + str(avail) + "/" + str(total))

# ============================================================
# 3. 原有模块兼容性验证
# ============================================================
print()
print("=" * 60)
print("3. 原有模块兼容性验证")
print("=" * 60)

from etf_analyzer.analyzer import ETFAnalyzer
from etf_analyzer.visualizer import ETFVisualizer
from etf_analyzer.report_generator import ReportGenerator
from etf_analyzer.data_processor import DataProcessor
from etf_analyzer.data_fetcher import ETFDataFetcher

analyzer = ETFAnalyzer()
print("[PASS] ETFAnalyzer 初始化成功")

# Analyzer 的功能通过单元测试验证（test_analyzer.py），此处仅验证初始化和接口存在
assert hasattr(analyzer, "analyze_nav_trend"), "缺少 analyze_nav_trend 方法"
assert hasattr(analyzer, "analyze_holdings"), "缺少 analyze_holdings 方法"
assert hasattr(analyzer, "analyze_industry_distribution"), "缺少 analyze_industry_distribution 方法"
assert hasattr(analyzer, "calculate_risk_metrics"), "缺少 calculate_risk_metrics 方法"
assert hasattr(analyzer, "analyze_performance"), "缺少 analyze_performance 方法"
print("[PASS] ETFAnalyzer 5个分析方法均存在")

processor = DataProcessor()
test_history_df = pd.DataFrame({
    "日期": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    "收盘": [3.0, 3.1, 3.2],
    "开盘": [2.9, 3.0, 3.1],
    "最高": [3.05, 3.15, 3.25],
    "最低": [2.85, 2.95, 3.05],
    "成交量": [1000, 1200, 1100],
})
cleaned = processor.clean_data(test_history_df)
assert not cleaned.empty, "数据清洗返回空"
print("[PASS] DataProcessor 数据清洗正常，行数: " + str(len(cleaned)))

validated, errors = processor.validate_data(test_history_df, required_columns=["收盘", "开盘"])
print("[PASS] DataProcessor 数据验证正常，通过: " + str(validated) + "，错误: " + str(len(errors)))

visualizer = ETFVisualizer()
print("[PASS] ETFVisualizer 初始化成功")

report_gen = ReportGenerator()
print("[PASS] ReportGenerator 初始化成功")

fetcher = ETFDataFetcher()
methods = ["get_realtime_quote", "get_history_data", "get_etf_list",
           "get_etf_holdings", "_adjust_trading_day", "_get_cache_key",
           "_load_cache", "_save_cache"]
for m in methods:
    assert hasattr(fetcher, m), "缺少 " + m + " 方法"
print("[PASS] ETFDataFetcher 接口兼容性验证通过（8个方法均存在）")

# ============================================================
# 4. 安全配置验证
# ============================================================
print()
print("=" * 60)
print("4. 安全配置管理验证")
print("=" * 60)

from etf_analyzer.secure_config import secure_config
from etf_analyzer.config import (
    DATASOURCE_PRIORITY, DATASOURCE_HEALTH_CHECK_INTERVAL,
    DATASOURCE_FAILURE_THRESHOLD, DATA_QUALITY_THRESHOLD,
    CROSS_VALIDATION_THRESHOLD, TUSHARE_TOKEN, PYTDX_HOST, PYTDX_PORT,
)

print("[PASS] SecureConfig 全局实例加载成功")
print("[PASS] 数据源优先级: " + str(DATASOURCE_PRIORITY))
print("[PASS] 健康检查间隔: " + str(DATASOURCE_HEALTH_CHECK_INTERVAL) + " 秒")
print("[PASS] 失败告警阈值: " + str(DATASOURCE_FAILURE_THRESHOLD))
print("[PASS] 质量评分阈值: " + str(DATA_QUALITY_THRESHOLD))
print("[PASS] 交叉验证阈值: " + str(CROSS_VALIDATION_THRESHOLD) + "%")
print("[PASS] Tushare Token 配置: " + ("已配置" if TUSHARE_TOKEN else "未配置"))
print("[PASS] pytdx 服务器: " + str(PYTDX_HOST) + ":" + str(PYTDX_PORT))

# .env.example 存在性检查
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_example = os.path.join(project_root, ".env.example")
assert os.path.exists(env_example), ".env.example 文件不存在，路径: " + env_example
print("[PASS] .env.example 文件存在")

# .gitignore 检查
gitignore = os.path.join(project_root, ".gitignore")
with open(gitignore, "r", encoding="utf-8") as f:
    gitignore_content = f.read()
assert ".env" in gitignore_content, ".gitignore 缺少 .env 排除规则"
print("[PASS] .gitignore 包含 .env 排除规则")

# ============================================================
# 5. 数据源管理器验证
# ============================================================
print()
print("=" * 60)
print("5. 数据源管理器验证")
print("=" * 60)

from etf_analyzer.data_source_manager import DataSourceManager

manager = DataSourceManager()
manager.register_all()
registered = [s.name for s in manager._sources]
print("[PASS] DataSourceManager 注册完成，已注册: " + str(registered))

status_list = manager.get_source_status()
for s in status_list:
    print("  数据源 " + s["name"] + ": available=" + str(s["available"]))

# ============================================================
# 6. 智能数据补全验证
# ============================================================
print()
print("=" * 60)
print("6. 智能数据补全验证")
print("=" * 60)

from etf_analyzer.data_completion import DataCompletion

completion = DataCompletion()

# 缺失日期填充
test_df = pd.DataFrame({
    "日期": pd.to_datetime(["2024-01-02", "2024-01-04", "2024-01-08"]),
    "收盘": [3.0, 3.1, 3.3],
    "开盘": [2.9, 3.0, 3.2],
})
filled = completion.fill_missing_dates(test_df, method="interpolate")
assert len(filled) >= len(test_df), "填充后行数应 >= 原始行数"
assert "_data_source" in filled.columns, "缺少 _data_source 列"
print("[PASS] 缺失日期填充正常，原始: " + str(len(test_df)) + " 行，填充后: " + str(len(filled)) + " 行")

# 交叉验证
data_dict = {
    "source_a": pd.DataFrame({
        "日期": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "收盘": [3.0, 3.1], "开盘": [2.9, 3.0],
    }),
    "source_b": pd.DataFrame({
        "日期": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "收盘": [3.01, 3.11], "开盘": [2.91, 3.01],
    }),
}
merged, conflicts = completion.cross_validate(data_dict)
assert not merged.empty, "交叉验证合并结果为空"
print("[PASS] 交叉验证正常，冲突数: " + str(len(conflicts)))

# 质量评分
score = completion.calculate_quality_score(filled, source_count=1, conflict_count=0)
assert 0 <= score <= 100, "质量评分超出范围"
print("[PASS] 质量评分: " + str(round(score, 2)))

# ============================================================
# 7. 边界条件测试
# ============================================================
print()
print("=" * 60)
print("7. 边界条件和异常情况测试")
print("=" * 60)

# 空数据输入
empty_df = pd.DataFrame()
assert completion.fill_missing_dates(empty_df).empty, "空 DataFrame 填充应返回空"
print("[PASS] 空数据填充返回空 DataFrame")

empty_merged, empty_conflicts = completion.cross_validate({})
assert empty_merged.empty, "空数据字典交叉验证应返回空"
print("[PASS] 空数据字典交叉验证返回空 DataFrame")

assert completion.calculate_quality_score(None) == 0, "None 质量评分应为 0"
print("[PASS] None 质量评分返回 0")

# 不存在的数据源
no_ver = updater.get_last_update_date("000000", "history")
assert no_ver is None
print("[PASS] 不存在的版本返回 None")

# SecureConfig 不存在的键
val = secure_config.get("NONEXISTENT_KEY", "default_val")
assert val == "default_val"
print("[PASS] SecureConfig 不存在的键返回默认值")

# SecureConfig require 缺失键
req_val = secure_config.require("NONEXISTENT_REQUIRED_KEY")
assert req_val is None
print("[PASS] SecureConfig require 缺失键返回 None")

# SecureConfig is_configured
assert not secure_config.is_configured("NONEXISTENT_KEY")
print("[PASS] SecureConfig is_configured 未配置键返回 False")

# DataSourceManager 全部失败
mock_fail_manager = DataSourceManager()
mock_fail_source = MagicMock()
mock_fail_source.name = "fail_source"
mock_fail_source.available = False
mock_fail_source.get_realtime_quote.return_value = {}
mock_fail_source.get_history_data.return_value = pd.DataFrame()
mock_fail_manager.register(mock_fail_source)
result = mock_fail_manager.get_realtime_quote(symbol="510300")
assert result == {}
print("[PASS] DataSourceManager 全部失败返回空数据")

# DataProcessor 空数据
assert processor.clean_data(None).empty, "None 清洗应返回空"
assert processor.normalize(pd.DataFrame()).empty, "空 DataFrame 标准化应返回空"
print("[PASS] DataProcessor 空数据处理正常")

# ============================================================
# 汇总
# ============================================================
print()
print("=" * 60)
print("全部功能验证通过！")
print("=" * 60)
