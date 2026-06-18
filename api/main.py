# -*- coding: utf-8 -*-
"""
FastAPI 应用入口

创建 FastAPI 应用实例，配置 CORS、路由挂载和生命周期事件。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from api.routers import etf, analysis, chart, report, strategy, backtest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库连接。"""
    try:
        from db.database import init_db
        init_db()
    except Exception:
        # 数据库不可用时优雅降级，API 仍可使用非数据库功能
        pass
    yield


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    settings = get_settings()

    app = FastAPI(
        title="ETF Analyzer API",
        description="ETF 分析工具 RESTful API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    api_prefix = settings.server.api_prefix
    app.include_router(etf.router, prefix=api_prefix)
    app.include_router(analysis.router, prefix=api_prefix)
    app.include_router(chart.router, prefix=api_prefix)
    app.include_router(report.router, prefix=api_prefix)
    app.include_router(strategy.router, prefix=api_prefix)
    app.include_router(backtest.router, prefix=api_prefix)

    return app


app = create_app()
