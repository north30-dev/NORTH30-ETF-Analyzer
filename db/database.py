# -*- coding: utf-8 -*-
"""
数据库连接和会话管理

提供 SQLAlchemy 引擎、会话工厂和依赖注入函数。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config.settings import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


def create_database_engine(url=None, **kwargs):
    """创建数据库引擎。

    Args:
        url: 数据库连接 URL，默认从配置读取。
        **kwargs: 传递给 create_engine 的额外参数。

    Returns:
        SQLAlchemy Engine 实例。
    """
    if url is None:
        settings = get_settings()
        url = settings.database.url
        kwargs.setdefault("pool_size", settings.database.pool_size)
        kwargs.setdefault("max_overflow", settings.database.max_overflow)
        kwargs.setdefault("pool_recycle", settings.database.pool_recycle)
        # MySQL 连接需要 charset 参数
        if "charset" not in url:
            url += "?charset=utf8mb4"
    kwargs.setdefault("echo", False)
    return create_engine(url, **kwargs)


# 默认引擎和会话工厂（延迟初始化）
_engine = None
_SessionLocal = None


def get_engine():
    """获取全局数据库引擎（单例）。"""
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


def get_session_factory():
    """获取全局会话工厂（单例）。"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    """FastAPI 依赖注入：获取数据库会话。

    Yields:
        SQLAlchemy Session 实例。
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine=None):
    """初始化数据库，创建所有表。

    Args:
        engine: 可选的 SQLAlchemy Engine，默认使用全局引擎。
    """
    if engine is None:
        engine = get_engine()
    # 导入所有模型以确保它们被注册
    import db.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def reset_engine():
    """重置全局引擎和会话工厂（主要用于测试）。"""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
