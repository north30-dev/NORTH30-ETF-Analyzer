# -*- coding: utf-8 -*-
"""API 路由单元测试"""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.deps import get_fetcher, get_analyzer


@pytest.fixture
def client():
    """创建测试客户端，每个测试后清理依赖覆盖。"""
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestETFRouter:
    """ETF 数据查询路由测试"""

    def test_get_etf_list(self, client):
        mock_fetcher = MagicMock()
        mock_fetcher.get_etf_list.return_value = pd.DataFrame({
            "代码": ["510300"], "名称": ["沪深300ETF"], "最新价": [3.5],
        })
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        response = client.get("/api/v1/etf/list")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_get_realtime_quote(self, client):
        mock_fetcher = MagicMock()
        mock_fetcher.get_realtime_quote.return_value = {
            "symbol": "510300", "name": "沪深300ETF", "price": 3.5,
        }
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        response = client.get("/api/v1/etf/510300/quote")
        assert response.status_code == 200

    def test_get_realtime_quote_not_found(self, client):
        mock_fetcher = MagicMock()
        mock_fetcher.get_realtime_quote.return_value = {}
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        response = client.get("/api/v1/etf/999999/quote")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404


class TestAnalysisRouter:
    """分析计算路由测试"""

    def test_analyze_nav_trend(self, client):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_nav_trend.return_value = {
            "cumulative_return": 10.5,
            "annualized_return": 5.2,
            "trend": "上升",
        }
        app.dependency_overrides[get_analyzer] = lambda: mock_analyzer

        response = client.post("/api/v1/analysis/nav-trend", json={
            "symbol": "510300",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_analyze_nav_trend_failed(self, client):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_nav_trend.return_value = None
        app.dependency_overrides[get_analyzer] = lambda: mock_analyzer

        response = client.post("/api/v1/analysis/nav-trend", json={
            "symbol": "999999",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404


class TestDocsEndpoint:
    """API 文档端点测试"""

    def test_docs_accessible(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_accessible(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
