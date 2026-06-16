# -*- coding: utf-8 -*-
"""Celery 异步任务单元测试"""

import pytest


class TestCeleryApp:
    """Celery 应用配置测试"""

    def test_celery_app_creation(self):
        """测试 Celery 应用实例创建。"""
        from tasks.celery_app import celery_app
        assert celery_app is not None
        assert celery_app.main == "etf_analyzer"

    def test_celery_config(self):
        """测试 Celery 配置。"""
        from tasks.celery_app import celery_app
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "Asia/Shanghai"


class TestReportTasks:
    """报告生成任务测试"""

    def test_generate_report_task(self):
        """测试报告生成任务。"""
        # 由于 Celery task 的 bind 机制，直接测试任务逻辑
        from tasks.report_tasks import generate_report

        # 验证任务已注册
        assert generate_report.name == "tasks.report_tasks.generate_report"


class TestBatchTasks:
    """批量分析任务测试"""

    def test_batch_analyze_task_registered(self):
        """测试批量分析任务已注册。"""
        from tasks.batch_tasks import batch_analyze
        assert batch_analyze.name == "tasks.batch_tasks.batch_analyze"
