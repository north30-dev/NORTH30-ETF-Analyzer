# -*- coding: utf-8 -*-
"""
数据异常预警模块

提供数据源健康状态监控、异常自动告警和数据质量报告生成功能，
帮助及时发现和处理数据源异常情况。
"""

from datetime import datetime

from etf_analyzer.config import (
    DATASOURCE_FAILURE_THRESHOLD,
    DATA_QUALITY_THRESHOLD,
)
from etf_analyzer.logger import setup_logger

# 告警事件最大保留数量
MAX_ALERT_EVENTS = 1000


class DataMonitor:
    """数据异常预警器，负责监控数据源健康状态并触发告警。

    通过定期检查数据源健康状态，跟踪连续失败次数和数据质量评分，
    在超过阈值时自动生成告警事件，并提供数据质量报告。

    Attributes:
        logger: 日志记录器实例。
    """

    def __init__(self, manager=None):
        """初始化 DataMonitor 实例。

        Args:
            manager: 可选的 DataSourceManager 实例，如果未提供则自动创建。
        """
        self.logger = setup_logger("data_monitor")
        self._manager = manager
        self._health_records = {}
        self._alert_events = []

    def _ensure_manager(self):
        """确保数据源管理器已初始化。

        如果未提供 DataSourceManager，则延迟创建并注册所有数据源。

        Returns:
            DataSourceManager: 数据源管理器实例，创建失败返回 None。
        """
        if self._manager is None:
            try:
                from etf_analyzer.data_source_manager import DataSourceManager
                self._manager = DataSourceManager()
                self._manager.register_all()
            except Exception as e:
                self.logger.error("初始化数据源管理器失败: %s", e)
                return None
        return self._manager

    def check_source_health(self, source_name=None):
        """检查数据源健康状态。

        如果指定 source_name，检查单个数据源；如果未指定，检查所有数据源。
        检查结果会更新到 _health_records 中。

        Args:
            source_name: 可选的数据源名称，如 "akshare"。未指定时检查所有数据源。

        Returns:
            dict: 健康状态字典。检查单个数据源时返回该数据源的状态；
                  检查所有数据源时返回以数据源名称为键的状态字典。
        """
        manager = self._ensure_manager()
        if manager is None:
            return {} if source_name is None else None

        now = datetime.now().isoformat()

        if source_name is not None:
            # 检查单个数据源
            source = manager._source_map.get(source_name)
            if source is None:
                self.logger.warning("数据源 '%s' 未注册", source_name)
                return None
            try:
                result = source.health_check()
            except Exception as e:
                self.logger.error("数据源 '%s' 健康检查异常: %s", source_name, e)
                result = {
                    "name": source_name,
                    "available": False,
                    "response_time": None,
                    "error": str(e),
                }
            self._update_health_record(source_name, result, now)
            return self._health_records.get(source_name)

        # 检查所有数据源
        manager.health_check_all()
        for source in manager._sources:
            health = manager._health_status.get(source.name)
            if health is not None:
                self._update_health_record(source.name, health, now)
            else:
                # 尚未执行过健康检查的数据源，记录默认状态
                self._update_health_record(source.name, {
                    "name": source.name,
                    "available": source.available,
                    "response_time": None,
                    "error": None,
                }, now)
        return dict(self._health_records)

    def _update_health_record(self, source_name, health_result, check_time):
        """更新单个数据源的健康记录。

        根据健康检查结果更新连续失败次数、总检查次数和总失败次数等统计信息。

        Args:
            source_name: 数据源名称。
            health_result: 健康检查结果字典，包含 available、response_time 等字段。
            check_time: 检查时间的 ISO 格式字符串。
        """
        available = health_result.get("available", False)
        response_time = health_result.get("response_time")

        existing = self._health_records.get(source_name, {})
        consecutive_failures = existing.get("consecutive_failures", 0)
        total_checks = existing.get("total_checks", 0)
        total_failures = existing.get("total_failures", 0)

        if available:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            total_failures += 1

        total_checks += 1

        self._health_records[source_name] = {
            "available": available,
            "response_time": response_time,
            "last_check_time": check_time,
            "consecutive_failures": consecutive_failures,
            "total_checks": total_checks,
            "total_failures": total_failures,
        }

    def get_health_status(self, source_name=None):
        """获取数据源健康状态。

        Args:
            source_name: 可选的数据源名称。未指定时返回所有数据源的状态。

        Returns:
            dict: 健康状态字典，包含 available、response_time、last_check_time、
                  consecutive_failures 等字段。
        """
        if source_name is not None:
            return self._health_records.get(source_name)
        return dict(self._health_records)

    def check_and_alert(self):
        """检查数据源健康状态并触发告警。

        执行健康检查后，检查以下告警条件：
        1. 连续失败次数是否超过 DATASOURCE_FAILURE_THRESHOLD（默认3次）
        2. 数据质量评分是否低于 DATA_QUALITY_THRESHOLD（默认60分）

        超过阈值时记录 WARNING 日志，并将告警事件添加到 _alert_events 列表。

        Returns:
            list: 本次检查产生的告警事件列表。
        """
        self.check_source_health()

        new_alerts = []
        now = datetime.now().isoformat()

        for source_name, record in self._health_records.items():
            # 检查连续失败次数
            consecutive = record.get("consecutive_failures", 0)
            if consecutive >= DATASOURCE_FAILURE_THRESHOLD:
                suggestion = self._get_failure_suggestion(source_name)
                alert = {
                    "time": now,
                    "source": source_name,
                    "level": "WARNING",
                    "type": "consecutive_failure",
                    "message": f"数据源 {source_name} 连续失败 {consecutive} 次",
                    "suggestion": suggestion,
                }
                self.logger.warning(
                    "数据源 %s 连续失败 %d 次，建议: %s",
                    source_name, consecutive, suggestion,
                )
                new_alerts.append(alert)

            # 检查数据质量评分
            quality_score = self._calc_quality_score(source_name, record)
            if quality_score < DATA_QUALITY_THRESHOLD:
                alert = {
                    "time": now,
                    "source": source_name,
                    "level": "WARNING",
                    "type": "low_quality",
                    "message": f"数据源 {source_name} 质量评分 {quality_score:.1f} 低于阈值 {DATA_QUALITY_THRESHOLD}",
                    "suggestion": f"请检查数据源 {source_name} 的数据完整性和准确性",
                }
                self.logger.warning(
                    "数据源 %s 质量评分 %.1f 低于阈值 %d",
                    source_name, quality_score, DATA_QUALITY_THRESHOLD,
                )
                new_alerts.append(alert)

        # 添加告警事件并限制最大数量
        self._alert_events.extend(new_alerts)
        if len(self._alert_events) > MAX_ALERT_EVENTS:
            self._alert_events = self._alert_events[-MAX_ALERT_EVENTS:]

        return new_alerts

    def _calc_quality_score(self, source_name, record):
        """计算数据源质量评分。

        评分规则：
        - 可用性得分：可用 70 分，不可用 0 分
        - 响应时间得分：响应时间越短得分越高（满分 20 分）
        - 稳定性得分：失败率越低得分越高（满分 10 分）

        Args:
            source_name: 数据源名称。
            record: 健康记录字典。

        Returns:
            float: 质量评分，范围 0-100。
        """
        # 可用性得分（满分70）
        availability_score = 70.0 if record.get("available", False) else 0.0

        # 响应时间得分（满分20）
        response_time = record.get("response_time")
        if response_time is not None and record.get("available", False):
            if response_time <= 1.0:
                time_score = 20.0
            elif response_time <= 3.0:
                time_score = 15.0
            elif response_time <= 5.0:
                time_score = 10.0
            elif response_time <= 10.0:
                time_score = 5.0
            else:
                time_score = 0.0
        else:
            time_score = 0.0

        # 稳定性得分（满分10）
        total_checks = record.get("total_checks", 0)
        total_failures = record.get("total_failures", 0)
        if total_checks > 0:
            failure_rate = total_failures / total_checks
            stability_score = max(0.0, 10.0 * (1.0 - failure_rate))
        else:
            stability_score = 10.0

        return availability_score + time_score + stability_score

    def _get_failure_suggestion(self, source_name):
        """根据数据源名称返回故障建议操作。

        Args:
            source_name: 数据源名称。

        Returns:
            str: 建议操作文本。
        """
        suggestions = {
            "akshare": "请检查网络连接是否正常，akshare 依赖网络访问",
            "tushare": "请检查 TUSHARE_TOKEN 配置是否正确",
            "baostock": "请检查网络连接是否正常，baostock 需要登录服务器",
            "pytdx": "请检查 PYTDX_HOST 和 PYTDX_PORT 配置是否正确",
        }
        return suggestions.get(
            source_name,
            f"请检查数据源 {source_name} 的配置和网络连接",
        )

    def get_alert_events(self, limit=50):
        """获取最近的告警事件列表。

        Args:
            limit: 返回的最大事件数量，默认50。

        Returns:
            list: 告警事件列表，按时间倒序排列（最新在前）。
        """
        return list(reversed(self._alert_events[-limit:]))

    def generate_quality_report(self):
        """生成数据质量报告。

        Returns:
            dict: 质量报告字典，包含：
                report_time: 报告生成时间
                sources: 各数据源健康状态
                summary: 摘要信息（total_sources、available_sources、unavailable_sources）
                alerts: 最近的告警事件
                recommendations: 建议操作列表
        """
        now = datetime.now().isoformat()

        # 确保有最新的健康状态数据
        self.check_source_health()

        sources = dict(self._health_records)
        unavailable = [
            name for name, record in sources.items()
            if not record.get("available", False)
        ]

        recommendations = []
        for name in unavailable:
            suggestion = self._get_failure_suggestion(name)
            recommendations.append(f"[{name}] {suggestion}")

        # 检查低质量数据源
        for name, record in sources.items():
            if record.get("available", False):
                score = self._calc_quality_score(name, record)
                if score < DATA_QUALITY_THRESHOLD:
                    recommendations.append(
                        f"[{name}] 数据质量评分 {score:.1f} 偏低，建议检查数据完整性"
                    )

        report = {
            "report_time": now,
            "sources": sources,
            "summary": {
                "total_sources": len(sources),
                "available_sources": len(sources) - len(unavailable),
                "unavailable_sources": unavailable,
            },
            "alerts": self.get_alert_events(),
            "recommendations": recommendations,
        }
        return report

    def format_quality_report(self, report=None):
        """将质量报告格式化为可读文本。

        Args:
            report: 可选的质量报告字典。如果未提供，则自动生成。

        Returns:
            str: 格式化后的多行文本报告。
        """
        if report is None:
            report = self.generate_quality_report()

        lines = []
        lines.append("=" * 60)
        lines.append("数据质量报告")
        lines.append(f"生成时间: {report['report_time']}")
        lines.append("=" * 60)

        # 摘要
        summary = report.get("summary", {})
        lines.append("")
        lines.append("【摘要】")
        lines.append(f"  数据源总数: {summary.get('total_sources', 0)}")
        lines.append(f"  可用数据源: {summary.get('available_sources', 0)}")
        unavailable = summary.get("unavailable_sources", [])
        if unavailable:
            lines.append(f"  不可用数据源: {', '.join(unavailable)}")
        else:
            lines.append("  不可用数据源: 无")

        # 各数据源状态
        sources = report.get("sources", {})
        if sources:
            lines.append("")
            lines.append("【数据源状态】")
            lines.append(
                f"  {'名称':<12} {'可用':<6} {'响应时间':<10} "
                f"{'连续失败':<8} {'质量评分':<8}"
            )
            lines.append("  " + "-" * 50)
            for name, record in sources.items():
                available = "是" if record.get("available", False) else "否"
                response_time = record.get("response_time")
                rt_str = f"{response_time:.2f}s" if response_time is not None else "N/A"
                consecutive = record.get("consecutive_failures", 0)
                score = self._calc_quality_score(name, record)
                lines.append(
                    f"  {name:<12} {available:<6} {rt_str:<10} "
                    f"{consecutive:<8} {score:<8.1f}"
                )

        # 告警事件
        alerts = report.get("alerts", [])
        lines.append("")
        lines.append("【最近告警】")
        if alerts:
            for alert in alerts[:10]:
                lines.append(
                    f"  [{alert.get('time', '')}] "
                    f"[{alert.get('level', '')}] "
                    f"{alert.get('source', '')} - {alert.get('message', '')}"
                )
                if alert.get("suggestion"):
                    lines.append(f"    建议: {alert['suggestion']}")
        else:
            lines.append("  无告警事件")

        # 建议
        recommendations = report.get("recommendations", [])
        lines.append("")
        lines.append("【建议操作】")
        if recommendations:
            for rec in recommendations:
                lines.append(f"  - {rec}")
        else:
            lines.append("  无建议操作")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
