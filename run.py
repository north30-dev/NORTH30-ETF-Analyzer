# -*- coding: utf-8 -*-
"""
ETF 分析工具启动脚本

支持一键启动 API 服务和 Celery Worker。
"""

import sys
import argparse


def start_api(host="0.0.0.0", port=8000):
    """启动 FastAPI 服务。"""
    import uvicorn
    from config.settings import get_settings

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=host or settings.server.host,
        port=port or settings.server.port,
        reload=settings.server.debug,
    )


def start_celery():
    """启动 Celery Worker。"""
    from tasks.celery_app import celery_app
    celery_app.worker_main(["worker", "--loglevel=info"])


def main():
    parser = argparse.ArgumentParser(description="ETF 分析工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # API 服务命令
    api_parser = subparsers.add_parser("api", help="启动 API 服务")
    api_parser.add_argument("--host", default=None, help="监听地址")
    api_parser.add_argument("--port", type=int, default=None, help="监听端口")

    # Celery Worker 命令
    subparsers.add_parser("celery", help="启动 Celery Worker")

    args = parser.parse_args()

    if args.command == "api":
        start_api(host=args.host, port=args.port)
    elif args.command == "celery":
        start_celery()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
