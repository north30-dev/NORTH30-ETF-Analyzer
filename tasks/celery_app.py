# -*- coding: utf-8 -*-
"""
Celery 应用配置

初始化 Celery 应用实例，配置 broker、backend 和序列化方式。
"""

from celery import Celery

from config.settings import get_settings


def create_celery_app() -> Celery:
    """创建 Celery 应用实例。"""
    settings = get_settings()
    celery_settings = settings.celery

    app = Celery(
        "etf_analyzer",
        broker=celery_settings.broker_url,
        backend=celery_settings.result_backend,
    )

    app.conf.update(
        task_serializer=celery_settings.task_serializer,
        result_serializer=celery_settings.result_serializer,
        accept_content=celery_settings.accept_content,
        timezone=celery_settings.timezone,
        enable_utc=celery_settings.enable_utc,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )

    # 自动发现任务模块
    app.autodiscover_tasks(["tasks"])

    return app


# 全局 Celery 应用实例
celery_app = create_celery_app()
