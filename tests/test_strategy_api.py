# -*- coding: utf-8 -*-
"""
策略与回测 API 接口测试

使用 FastAPI TestClient 测试策略管理和回测管理的 RESTful API 端点。
所有数据获取均通过 mock 避免真实网络请求。
"""

from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.routers.strategy import _strategy_cache
from api.routers.backtest import _backtest_cache, _backtest_history

# 显式导入策略模块，触发 @register_strategy 装饰器注册
import etf_analyzer.strategies.momentum  # noqa: F401
import etf_analyzer.strategies.mean_reversion  # noqa: F401
import etf_analyzer.strategies.sector_rotation  # noqa: F401
import etf_analyzer.strategies.multi_factor  # noqa: F401


# ============================================================
# 辅助函数
# ============================================================


def create_test_data(days=100, start_price=10.0, trend=0.001, volatility=0.02):
    """生成模拟ETF数据"""
    dates = pd.date_range(start="2024-01-01", periods=days, freq="B")
    np.random.seed(42)
    returns = np.random.normal(trend, volatility, days)
    close = start_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.01, days)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, days)))
    open_price = close * (1 + np.random.normal(0, 0.005, days))
    volume = np.random.randint(100000, 1000000, days)

    return pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


# 模拟数据加载的返回值
MOCK_DATA = create_test_data(days=100)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_caches():
    """每个测试前后清理缓存"""
    _strategy_cache.clear()
    _backtest_cache.clear()
    _backtest_history.clear()
    yield
    _strategy_cache.clear()
    _backtest_cache.clear()
    _backtest_history.clear()


@pytest.fixture
def mock_data_loader():
    """Mock BacktestDataLoader.load_from_api 返回模拟数据"""
    with patch(
        "api.routers.strategy.BacktestDataLoader.load_from_api",
        return_value=MOCK_DATA,
    ), patch(
        "api.routers.strategy.BacktestDataLoader.load_from_csv",
        return_value=MOCK_DATA,
    ), patch(
        "api.routers.strategy.BacktestDataLoader.load_from_database",
        return_value=MOCK_DATA,
    ), patch(
        "api.routers.backtest.BacktestDataLoader.load_from_api",
        return_value=MOCK_DATA,
    ), patch(
        "api.routers.backtest.BacktestDataLoader.load_from_database",
        return_value=MOCK_DATA,
    ):
        yield


# ============================================================
# 策略管理 API 测试
# ============================================================


class TestStrategyAPI:
    """策略管理 API 测试"""

    def test_list_strategies(self, client):
        """测试 GET /api/v1/strategy/list"""
        response = client.get("/api/v1/strategy/list")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert "strategies" in data["data"]

        strategies = data["data"]["strategies"]
        strategy_names = [s["name"] for s in strategies]
        assert "momentum" in strategy_names
        assert "mean_reversion" in strategy_names
        assert "sector_rotation" in strategy_names
        assert "multi_factor" in strategy_names

    def test_get_strategy_params(self, client):
        """测试 GET /api/v1/strategy/{strategy_name}/params"""
        response = client.get("/api/v1/strategy/momentum/params")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert data["data"]["strategy_name"] == "momentum"
        assert "params" in data["data"]
        assert data["data"]["params"]["period"] == 20

    def test_get_strategy_params_not_found(self, client):
        """测试获取不存在的策略参数返回404"""
        response = client.get("/api/v1/strategy/nonexistent/params")
        assert response.status_code == 404

    def test_update_strategy_params(self, client):
        """测试 PUT /api/v1/strategy/{strategy_name}/params"""
        response = client.put(
            "/api/v1/strategy/momentum/params",
            json={"params": {"period": 30}},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert data["data"]["params"]["period"] == 30

    def test_update_strategy_params_invalid(self, client):
        """测试更新非法策略参数返回400"""
        response = client.put(
            "/api/v1/strategy/momentum/params",
            json={"params": {"period": -1}},
        )
        assert response.status_code == 400

    def test_update_strategy_params_not_found(self, client):
        """测试更新不存在的策略参数返回404"""
        response = client.put(
            "/api/v1/strategy/nonexistent/params",
            json={"params": {"period": 30}},
        )
        assert response.status_code == 404

    def test_generate_signals(self, client, mock_data_loader):
        """测试 POST /api/v1/strategy/{strategy_name}/signals"""
        response = client.post(
            "/api/v1/strategy/momentum/signals",
            json={
                "symbol": "510300",
                "start_date": "20240101",
                "end_date": "20240601",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert data["data"]["strategy_name"] == "momentum"
        assert data["data"]["symbol"] == "510300"
        assert "signals" in data["data"]
        assert isinstance(data["data"]["signals"], list)

    def test_generate_signals_not_found_strategy(self, client, mock_data_loader):
        """测试对不存在的策略生成信号返回404"""
        response = client.post(
            "/api/v1/strategy/nonexistent/signals",
            json={"symbol": "510300"},
        )
        assert response.status_code == 404

    def test_generate_signals_data_load_failure(self, client):
        """测试数据加载失败时返回400"""
        with patch(
            "api.routers.strategy.BacktestDataLoader.load_from_api",
            return_value=pd.DataFrame(),
        ):
            response = client.post(
                "/api/v1/strategy/momentum/signals",
                json={"symbol": "510300"},
            )
            assert response.status_code == 400


# ============================================================
# 回测管理 API 测试
# ============================================================


class TestBacktestAPI:
    """回测管理 API 测试"""

    def test_run_backtest(self, client, mock_data_loader):
        """测试 POST /api/v1/backtest/run"""
        response = client.post(
            "/api/v1/backtest/run",
            json={
                "strategy_name": "momentum",
                "symbol": "510300",
                "start_date": "20240101",
                "end_date": "20240601",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert "backtest_id" in data["data"]
        assert data["data"]["strategy_name"] == "momentum"
        assert data["data"]["symbol"] == "510300"
        assert "performance" in data["data"]

    def test_run_backtest_strategy_not_found(self, client, mock_data_loader):
        """测试对不存在的策略执行回测返回404"""
        response = client.post(
            "/api/v1/backtest/run",
            json={"strategy_name": "nonexistent", "symbol": "510300"},
        )
        assert response.status_code == 404

    def test_run_backtest_data_load_failure(self, client):
        """测试数据加载失败时回测返回400"""
        with patch(
            "api.routers.backtest.BacktestDataLoader.load_from_api",
            return_value=pd.DataFrame(),
        ), patch(
            "api.routers.backtest.BacktestDataLoader.load_from_database",
            return_value=pd.DataFrame(),
        ):
            response = client.post(
                "/api/v1/backtest/run",
                json={"strategy_name": "momentum", "symbol": "510300"},
            )
            assert response.status_code == 400

    def test_get_backtest_result(self, client, mock_data_loader):
        """测试 GET /api/v1/backtest/{backtest_id}/result"""
        # 先执行一次回测
        run_response = client.post(
            "/api/v1/backtest/run",
            json={"strategy_name": "momentum", "symbol": "510300"},
        )
        backtest_id = run_response.json()["data"]["backtest_id"]

        # 查询回测结果
        response = client.get(f"/api/v1/backtest/{backtest_id}/result")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert data["data"]["backtest_id"] == backtest_id
        assert "performance" in data["data"]
        assert "trades" in data["data"]
        assert "equity_curve" in data["data"]

    def test_get_backtest_result_not_found(self, client):
        """测试查询不存在的回测ID返回404"""
        response = client.get("/api/v1/backtest/nonexistent-id/result")
        assert response.status_code == 404

    def test_compare_strategies(self, client, mock_data_loader):
        """测试 POST /api/v1/backtest/compare"""
        response = client.post(
            "/api/v1/backtest/compare",
            json={
                "strategy_names": ["momentum", "mean_reversion"],
                "symbol": "510300",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert "results" in data["data"]
        assert "momentum" in data["data"]["results"]
        assert "mean_reversion" in data["data"]["results"]

    def test_compare_strategies_not_found(self, client, mock_data_loader):
        """测试对比不存在的策略返回404"""
        response = client.post(
            "/api/v1/backtest/compare",
            json={
                "strategy_names": ["nonexistent"],
                "symbol": "510300",
            },
        )
        assert response.status_code == 404

    def test_compare_strategies_data_load_failure(self, client):
        """测试对比时数据加载失败返回400"""
        with patch(
            "api.routers.backtest.BacktestDataLoader.load_from_api",
            return_value=pd.DataFrame(),
        ), patch(
            "api.routers.backtest.BacktestDataLoader.load_from_database",
            return_value=pd.DataFrame(),
        ):
            response = client.post(
                "/api/v1/backtest/compare",
                json={
                    "strategy_names": ["momentum"],
                    "symbol": "510300",
                },
            )
            assert response.status_code == 400

    def test_optimize_params(self, client, mock_data_loader):
        """测试 POST /api/v1/backtest/optimize"""
        response = client.post(
            "/api/v1/backtest/optimize",
            json={
                "strategy_name": "momentum",
                "symbol": "510300",
                "param_grid": {"period": [10, 20]},
                "metric": "sharpe_ratio",
                "top_n": 2,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert "best_params" in data["data"]
        assert "best_metric_value" in data["data"]
        assert "top_results" in data["data"]
        assert data["data"]["total_combinations"] == 2

    def test_optimize_params_strategy_not_found(self, client, mock_data_loader):
        """测试对不存在的策略寻优返回404"""
        response = client.post(
            "/api/v1/backtest/optimize",
            json={
                "strategy_name": "nonexistent",
                "symbol": "510300",
                "param_grid": {"period": [10, 20]},
            },
        )
        assert response.status_code == 404

    def test_optimize_params_data_load_failure(self, client):
        """测试寻优时数据加载失败返回400"""
        with patch(
            "api.routers.backtest.BacktestDataLoader.load_from_api",
            return_value=pd.DataFrame(),
        ), patch(
            "api.routers.backtest.BacktestDataLoader.load_from_database",
            return_value=pd.DataFrame(),
        ):
            response = client.post(
                "/api/v1/backtest/optimize",
                json={
                    "strategy_name": "momentum",
                    "symbol": "510300",
                    "param_grid": {"period": [10, 20]},
                },
            )
            assert response.status_code == 400

    def test_get_backtest_history(self, client, mock_data_loader):
        """测试 GET /api/v1/backtest/history"""
        # 先执行一次回测以产生历史记录
        client.post(
            "/api/v1/backtest/run",
            json={"strategy_name": "momentum", "symbol": "510300"},
        )

        response = client.get("/api/v1/backtest/history")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert "history" in data["data"]
        assert len(data["data"]["history"]) > 0

    def test_get_backtest_history_empty(self, client):
        """测试无回测历史时返回空列表"""
        response = client.get("/api/v1/backtest/history")
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert data["data"]["history"] == []

    def test_run_backtest_with_custom_params(self, client, mock_data_loader):
        """测试带自定义参数的回测"""
        response = client.post(
            "/api/v1/backtest/run",
            json={
                "strategy_name": "momentum",
                "symbol": "510300",
                "params": {"period": 30, "buy_threshold": 0.03},
                "initial_capital": 500000.0,
                "commission_rate": 0.0005,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["code"] == 0
        assert "performance" in data["data"]
