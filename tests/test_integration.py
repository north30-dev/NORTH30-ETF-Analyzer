# -*- coding: utf-8 -*-
"""
端到端集成测试

验证 API + 数据库 + 依赖注入的联动，覆盖：
1. API + 数据库集成测试
2. API 路由集成测试
3. 配置系统集成测试
4. 数据库 CRUD 集成测试
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.main import app
from api.deps import get_fetcher, get_analyzer, get_visualizer, get_report_generator
from config.settings import Settings, get_settings, reset_settings
from db.database import Base, get_db
from db.models import ETFInfo, HistoryDataCache
from db.crud import (
    create_etf_info, get_etf_info, get_etf_info_list, upsert_etf_info,
    bulk_upsert_etf_info, get_history_data, get_latest_trade_date,
    bulk_insert_history_data, delete_history_data,
)


# ============================================================
# 公共 fixtures
# ============================================================

@pytest.fixture
def db_engine():
    """创建 SQLite 内存数据库引擎。"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """创建测试数据库会话。"""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def override_get_db(db_engine):
    """覆盖 FastAPI 的 get_db 依赖，使用内存数据库。"""
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    return _get_db


@pytest.fixture
def client(override_get_db):
    """创建测试客户端，覆盖数据库依赖，每个测试后清理。"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def populated_db(db_session):
    """预填充 ETF 和历史数据的数据库会话。"""
    create_etf_info(db_session, "510300", "沪深300ETF", scale=500.0)
    create_etf_info(db_session, "510500", "中证500ETF", scale=300.0)
    create_etf_info(db_session, "159915", "创业板ETF", scale=200.0)

    bulk_insert_history_data(db_session, [
        {"symbol": "510300", "trade_date": "2024-01-02", "open": 3.5, "close": 3.6,
         "high": 3.7, "low": 3.4, "volume": 1000000, "amount": 3500000},
        {"symbol": "510300", "trade_date": "2024-01-03", "open": 3.6, "close": 3.55,
         "high": 3.65, "low": 3.5, "volume": 1100000, "amount": 3900000},
        {"symbol": "510300", "trade_date": "2024-01-04", "open": 3.55, "close": 3.7,
         "high": 3.75, "low": 3.5, "volume": 1200000, "amount": 4300000},
        {"symbol": "510500", "trade_date": "2024-01-02", "open": 6.1, "close": 6.2,
         "high": 6.3, "low": 6.0, "volume": 800000, "amount": 4900000},
    ])
    return db_session


# ============================================================
# 1. API + 数据库集成测试
# ============================================================

class TestAPIDatabaseIntegration:
    """API 与数据库联动集成测试"""

    def test_etf_list_api_reads_from_database(self, client, db_engine, override_get_db):
        """测试 ETF 列表查询 API 能正确从数据库读取数据。

        模拟 fetcher 从数据库读取 ETF 列表数据，验证 API 返回结果与数据库一致。
        """
        # 先通过 CRUD 向数据库写入数据
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = TestSession()
        create_etf_info(session, "510300", "沪深300ETF")
        create_etf_info(session, "510500", "中证500ETF")
        session.close()

        # 创建 mock fetcher，模拟从数据库读取数据
        mock_fetcher = MagicMock()
        mock_fetcher.get_etf_list.return_value = pd.DataFrame({
            "代码": ["510300", "510500"],
            "名称": ["沪深300ETF", "中证500ETF"],
            "最新价": [3.6, 6.2],
        })
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        response = client.get("/api/v1/etf/list")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 2
        assert data["data"][0]["代码"] == "510300"
        assert data["data"][1]["代码"] == "510500"

    def test_etf_create_then_query_via_api(self, client, db_engine, override_get_db):
        """测试 ETF 信息创建后能通过 API 查询到。

        通过 CRUD 创建 ETF 信息，再通过 mock fetcher 读取并经 API 返回，
        验证数据在数据库和 API 之间的一致性。
        """
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = TestSession()

        # 创建 ETF 信息
        etf = create_etf_info(session, "159915", "创业板ETF", scale=200.0)
        assert etf.symbol == "159915"

        # 验证数据库中存在
        result = get_etf_info(session, "159915")
        assert result is not None
        assert result.name == "创业板ETF"
        assert result.scale == 200.0
        session.close()

        # 通过 API 查询（mock fetcher 返回与数据库一致的数据）
        mock_fetcher = MagicMock()
        mock_fetcher.get_realtime_quote.return_value = {
            "symbol": "159915", "name": "创业板ETF", "price": 2.15,
        }
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        response = client.get("/api/v1/etf/159915/quote")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["symbol"] == "159915"
        assert data["data"]["name"] == "创业板ETF"

    def test_history_data_write_then_query_via_api(self, client, db_engine, override_get_db):
        """测试历史数据写入后能通过 API 查询到。

        通过 CRUD 写入历史数据，再通过 mock fetcher 读取并经 API 返回，
        验证历史数据在数据库和 API 之间的一致性。
        """
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = TestSession()

        # 写入历史数据
        bulk_insert_history_data(session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-03", "close": 3.6},
        ])

        # 验证数据库中存在
        result = get_history_data(session, "510300")
        assert len(result) == 2
        assert result[0].close == 3.5
        assert result[1].close == 3.6
        session.close()

        # 通过 API 查询（mock fetcher 返回与数据库一致的数据）
        mock_fetcher = MagicMock()
        mock_fetcher.get_history_data.return_value = pd.DataFrame({
            "日期": ["2024-01-02", "2024-01-03"],
            "收盘": [3.5, 3.6],
        })
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        response = client.get("/api/v1/etf/510300/history")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 2


# ============================================================
# 2. API 路由集成测试
# ============================================================

class TestAPIRouteIntegration:
    """API 路由端到端集成测试"""

    def test_etf_query_full_flow(self, client):
        """测试完整的 ETF 查询流程：列表 → 详情 → 历史数据。"""
        # Step 1: 查询 ETF 列表
        mock_fetcher = MagicMock()
        mock_fetcher.get_etf_list.return_value = pd.DataFrame({
            "代码": ["510300"], "名称": ["沪深300ETF"], "最新价": [3.5],
        })
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        list_resp = client.get("/api/v1/etf/list")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["code"] == 0
        assert len(list_data["data"]) >= 1
        symbol = list_data["data"][0]["代码"]

        # Step 2: 查询 ETF 实时行情
        mock_fetcher.get_realtime_quote.return_value = {
            "symbol": symbol, "name": "沪深300ETF", "price": 3.5,
        }
        quote_resp = client.get(f"/api/v1/etf/{symbol}/quote")
        assert quote_resp.status_code == 200
        quote_data = quote_resp.json()
        assert quote_data["code"] == 0
        assert quote_data["data"]["symbol"] == symbol

        # Step 3: 查询 ETF 历史数据
        mock_fetcher.get_history_data.return_value = pd.DataFrame({
            "日期": ["2024-01-02", "2024-01-03"],
            "收盘": [3.5, 3.6],
        })
        history_resp = client.get(f"/api/v1/etf/{symbol}/history")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert history_data["code"] == 0
        assert len(history_data["data"]) == 2

    def test_analysis_api_end_to_end(self, client):
        """测试分析 API 端到端调用（使用 Mock 数据源）。"""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_nav_trend.return_value = {
            "cumulative_return": 10.5,
            "annualized_return": 5.2,
            "max_drawdown": -8.3,
            "trend": "上升",
            "nav_data": MagicMock(),  # 不可序列化的数据
        }
        app.dependency_overrides[get_analyzer] = lambda: mock_analyzer

        response = client.post("/api/v1/analysis/nav-trend", json={
            "symbol": "510300",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["cumulative_return"] == 10.5
        assert data["data"]["annualized_return"] == 5.2
        # nav_data 被过滤，不应出现在响应中
        assert "nav_data" not in data["data"]

    def test_chart_generate_api_end_to_end(self, client, tmp_path):
        """测试图表生成 API 端到端调用。"""
        mock_fetcher = MagicMock()
        mock_analyzer = MagicMock()
        mock_visualizer = MagicMock()

        # 模拟 fetcher 返回历史数据
        mock_fetcher.get_history_data.return_value = pd.DataFrame({
            "日期": ["2024-01-02", "2024-01-03"],
            "开盘": [3.5, 3.6],
            "收盘": [3.6, 3.55],
            "最高": [3.7, 3.65],
            "最低": [3.4, 3.5],
            "成交量": [1000000, 1100000],
        })

        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher
        app.dependency_overrides[get_analyzer] = lambda: mock_analyzer
        app.dependency_overrides[get_visualizer] = lambda: mock_visualizer

        # 使用 kline 图表类型测试
        with patch("api.routers.chart.CHART_DIR", str(tmp_path)):
            response = client.post("/api/v1/chart/generate", json={
                "symbol": "510300",
                "chart_type": "kline",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "url" in data["data"]
        assert "filename" in data["data"]
        mock_visualizer.plot_kline.assert_called_once()

    def test_report_generate_api_returns_task_id(self, client):
        """测试报告生成 API 返回 task_id（异步 Celery 任务）。"""
        mock_async_result = MagicMock()
        mock_async_result.id = "test-celery-task-123"

        with patch("api.routers.report.generate_report") as mock_task:
            mock_task.delay.return_value = mock_async_result

            response = client.post("/api/v1/report/generate", json={
                "symbol": "510300",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["task_id"] == "test-celery-task-123"
        assert data["data"]["status"] == "PENDING"

    def test_report_task_status_api(self, client):
        """测试报告任务状态查询 API。"""
        mock_result = MagicMock()
        mock_result.status = "PENDING"

        with patch("api.routers.report.AsyncResult", return_value=mock_result):
            response = client.get("/api/v1/report/task/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["task_id"] == "test-task-123"
        assert data["data"]["status"] == "PENDING"


# ============================================================
# 3. 配置系统集成测试
# ============================================================

class TestSettingsIntegration:
    """配置系统集成测试"""

    def test_settings_loads_default_config(self):
        """测试 Settings 能正确加载默认配置。"""
        settings = Settings()
        assert settings.server.host == "0.0.0.0"
        assert settings.server.port == 8000
        assert settings.server.api_prefix == "/api/v1"
        assert settings.database.driver == "mysql+pymysql"
        assert settings.analysis.risk_free_rate == 0.02
        assert settings.analysis.default_start_date == "20200101"
        assert settings.report.font == "SimHei"
        assert settings.cache.expire_hours == 4

    def test_settings_database_url_construction(self):
        """测试数据库 URL 正确构建。"""
        settings = Settings()
        url = settings.database.url
        assert "mysql+pymysql" in url
        assert "charset=utf8mb4" in url

    def test_settings_redis_url_construction(self):
        """测试 Redis URL 正确构建（无密码）。"""
        settings = Settings()
        url = settings.redis.url
        assert url.startswith("redis://")
        assert "127.0.0.1" in url
        assert "6379" in url

    def test_settings_redis_url_with_password(self):
        """测试 Redis URL 正确构建（有密码）。"""
        from config.settings import RedisSettings
        redis_with_pwd = RedisSettings(password="secret")
        url = redis_with_pwd.url
        assert ":secret@" in url

    def test_settings_celery_config(self):
        """测试 Celery 配置正确加载。"""
        settings = Settings()
        assert settings.celery.broker_url.startswith("redis://")
        assert settings.celery.task_serializer == "json"
        assert settings.celery.timezone == "Asia/Shanghai"
        assert settings.celery.enable_utc is False

    def test_settings_datasource_priority(self):
        """测试数据源优先级配置。"""
        settings = Settings()
        assert "akshare" in settings.datasource.priority
        assert len(settings.datasource.priority) >= 1

    def test_settings_env_switching(self):
        """测试不同环境配置能正确切换。"""
        # 默认环境
        settings_dev = Settings()
        assert settings_dev.env == "development"

        # 通过环境变量切换
        with patch.dict("os.environ", {"ETF_ENV": "testing"}):
            reset_settings()
            settings_test = Settings()
            assert settings_test.env == "testing"

        # 恢复
        reset_settings()

    def test_settings_deep_merge(self):
        """测试配置深度合并逻辑。"""
        base = {"server": {"host": "0.0.0.0", "port": 8000}, "debug": True}
        override = {"server": {"port": 9000}, "debug": False}
        result = Settings._deep_merge(base, override)
        assert result["server"]["host"] == "0.0.0.0"
        assert result["server"]["port"] == 9000
        assert result["debug"] is False

    def test_settings_industry_maps(self):
        """测试行业分类映射正确初始化。"""
        settings = Settings()
        assert len(settings.sw_industry_map) > 0
        assert "801780" in settings.sw_industry_map
        assert settings.sw_industry_map["801780"] == "银行"
        assert len(settings.zx_industry_map) > 0
        assert "CI005001" in settings.zx_industry_map

    def test_get_settings_singleton(self):
        """测试 get_settings 返回单例。"""
        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
        reset_settings()


# ============================================================
# 4. 数据库 CRUD 集成测试
# ============================================================

class TestCRUDIntegration:
    """数据库 CRUD 完整生命周期集成测试"""

    def test_etf_info_crud_lifecycle(self, db_session):
        """测试 ETFInfo 完整 CRUD 生命周期：创建 → 读取 → 更新 → 删除。"""
        # Create
        etf = create_etf_info(db_session, "510300", "沪深300ETF", scale=100.0)
        assert etf.id is not None
        assert etf.symbol == "510300"
        assert etf.name == "沪深300ETF"
        assert etf.scale == 100.0

        # Read
        found = get_etf_info(db_session, "510300")
        assert found is not None
        assert found.name == "沪深300ETF"
        assert found.scale == 100.0

        # Read list
        all_etfs = get_etf_info_list(db_session)
        assert len(all_etfs) == 1

        # Update (via upsert)
        updated = upsert_etf_info(db_session, "510300", "沪深300ETF更新", scale=200.0)
        assert updated.name == "沪深300ETF更新"
        assert updated.scale == 200.0

        # Verify update
        found_again = get_etf_info(db_session, "510300")
        assert found_again.name == "沪深300ETF更新"
        assert found_again.scale == 200.0

        # Delete (通过 session.delete)
        db_session.delete(found_again)
        db_session.commit()

        # Verify deletion
        deleted = get_etf_info(db_session, "510300")
        assert deleted is None

    def test_history_data_crud_lifecycle(self, db_session):
        """测试 HistoryDataCache 完整 CRUD 生命周期：创建 → 读取 → 更新 → 删除。"""
        # Create
        count = bulk_insert_history_data(db_session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "open": 3.5, "close": 3.6,
             "high": 3.7, "low": 3.4, "volume": 1000000, "amount": 3500000},
            {"symbol": "510300", "trade_date": "2024-01-03", "open": 3.6, "close": 3.55,
             "high": 3.65, "low": 3.5, "volume": 1100000, "amount": 3900000},
        ])
        assert count == 2

        # Read
        records = get_history_data(db_session, "510300")
        assert len(records) == 2
        assert records[0].close == 3.6
        assert records[1].close == 3.55

        # Read with date range
        filtered = get_history_data(db_session, "510300", start_date="2024-01-03")
        assert len(filtered) == 1
        assert filtered[0].trade_date == "2024-01-03"

        # Read latest trade date
        latest = get_latest_trade_date(db_session, "510300")
        assert latest == "2024-01-03"

        # Update (修改某条记录的字段)
        records[0].close = 3.65
        db_session.commit()
        updated = get_history_data(db_session, "510300", start_date="2024-01-02",
                                   end_date="2024-01-02")
        assert len(updated) == 1
        assert updated[0].close == 3.65

        # Delete
        deleted_count = delete_history_data(db_session, "510300")
        assert deleted_count == 2

        # Verify deletion
        empty = get_history_data(db_session, "510300")
        assert len(empty) == 0

    def test_bulk_upsert_etf_info_lifecycle(self, db_session):
        """测试批量 upsert ETF 信息的完整流程。"""
        # 首次批量插入
        etf_list = [
            {"symbol": "510300", "name": "沪深300ETF", "scale": 500.0},
            {"symbol": "510500", "name": "中证500ETF", "scale": 300.0},
            {"symbol": "159915", "name": "创业板ETF", "scale": 200.0},
        ]
        count = bulk_upsert_etf_info(db_session, etf_list)
        assert count == 3

        # 验证插入
        all_etfs = get_etf_info_list(db_session)
        assert len(all_etfs) == 3

        # 批量更新（更新已有 + 新增）
        updated_list = [
            {"symbol": "510300", "name": "沪深300ETF更新", "scale": 600.0},
            {"symbol": "510500", "name": "中证500ETF", "scale": 350.0},
            {"symbol": "510050", "name": "上证50ETF", "scale": 400.0},
        ]
        count2 = bulk_upsert_etf_info(db_session, updated_list)
        assert count2 == 3

        # 验证更新
        etf_300 = get_etf_info(db_session, "510300")
        assert etf_300.name == "沪深300ETF更新"
        assert etf_300.scale == 600.0

        # 验证新增
        all_etfs2 = get_etf_info_list(db_session)
        assert len(all_etfs2) == 4

    def test_etf_info_keyword_search(self, db_session):
        """测试 ETF 信息关键词搜索集成。"""
        create_etf_info(db_session, "510300", "沪深300ETF")
        create_etf_info(db_session, "510500", "中证500ETF")
        create_etf_info(db_session, "159915", "创业板ETF")

        # 按名称搜索
        result = get_etf_info_list(db_session, keyword="沪深")
        assert len(result) == 1
        assert result[0].symbol == "510300"

        # 按代码搜索
        result2 = get_etf_info_list(db_session, keyword="510")
        assert len(result2) == 2

        # 搜索无匹配
        result3 = get_etf_info_list(db_session, keyword="不存在的ETF")
        assert len(result3) == 0

    def test_history_data_date_range_query(self, db_session):
        """测试历史数据日期范围查询集成。"""
        bulk_insert_history_data(db_session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-03", "close": 3.6},
            {"symbol": "510300", "trade_date": "2024-01-04", "close": 3.7},
            {"symbol": "510300", "trade_date": "2024-01-05", "close": 3.8},
            {"symbol": "510500", "trade_date": "2024-01-02", "close": 6.2},
        ])

        # 查询全部
        all_data = get_history_data(db_session, "510300")
        assert len(all_data) == 4

        # 查询起始日期
        from_start = get_history_data(db_session, "510300", start_date="2024-01-03")
        assert len(from_start) == 3

        # 查询结束日期
        to_end = get_history_data(db_session, "510300", end_date="2024-01-03")
        assert len(to_end) == 2

        # 查询日期范围
        in_range = get_history_data(db_session, "510300",
                                    start_date="2024-01-03", end_date="2024-01-04")
        assert len(in_range) == 2

        # 查询不同 symbol
        other = get_history_data(db_session, "510500")
        assert len(other) == 1

    def test_history_data_partial_delete(self, db_session):
        """测试历史数据按日期范围部分删除。"""
        bulk_insert_history_data(db_session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-03", "close": 3.6},
            {"symbol": "510300", "trade_date": "2024-01-04", "close": 3.7},
        ])

        # 删除指定日期范围的数据
        deleted = delete_history_data(db_session, "510300",
                                      start_date="2024-01-02", end_date="2024-01-03")
        assert deleted == 2

        # 验证剩余数据
        remaining = get_history_data(db_session, "510300")
        assert len(remaining) == 1
        assert remaining[0].trade_date == "2024-01-04"


# ============================================================
# 5. 跨模块集成测试
# ============================================================

class TestCrossModuleIntegration:
    """跨模块联动集成测试"""

    def test_database_and_crud_consistency(self, db_engine):
        """测试数据库引擎和 CRUD 操作的一致性。

        使用同一个引擎创建多个会话，验证数据在不同会话间的一致性。
        """
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

        # 会话1：写入数据
        session1 = TestSession()
        create_etf_info(session1, "510300", "沪深300ETF")
        session1.close()

        # 会话2：读取数据
        session2 = TestSession()
        result = get_etf_info(session2, "510300")
        assert result is not None
        assert result.name == "沪深300ETF"
        session2.close()

    def test_api_with_database_populated(self, client, db_engine, override_get_db):
        """测试 API 在数据库有数据时的完整行为。

        模拟真实场景：数据库中已有缓存数据，API 通过 fetcher 返回数据。
        """
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = TestSession()

        # 预填充数据库
        create_etf_info(session, "510300", "沪深300ETF", scale=500.0)
        bulk_insert_history_data(session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-03", "close": 3.6},
        ])
        session.close()

        # 验证数据库状态
        verify_session = TestSession()
        etf = get_etf_info(verify_session, "510300")
        assert etf is not None
        history = get_history_data(verify_session, "510300")
        assert len(history) == 2
        verify_session.close()

        # mock fetcher 返回数据，模拟从缓存读取
        mock_fetcher = MagicMock()
        mock_fetcher.get_etf_list.return_value = pd.DataFrame({
            "代码": ["510300"], "名称": ["沪深300ETF"], "最新价": [3.55],
        })
        mock_fetcher.get_realtime_quote.return_value = {
            "symbol": "510300", "name": "沪深300ETF", "price": 3.55,
        }
        mock_fetcher.get_history_data.return_value = pd.DataFrame({
            "日期": ["2024-01-02", "2024-01-03"],
            "收盘": [3.5, 3.6],
        })
        app.dependency_overrides[get_fetcher] = lambda: mock_fetcher

        # 测试 API 响应
        list_resp = client.get("/api/v1/etf/list")
        assert list_resp.json()["code"] == 0

        quote_resp = client.get("/api/v1/etf/510300/quote")
        assert quote_resp.json()["code"] == 0

        history_resp = client.get("/api/v1/etf/510300/history")
        assert history_resp.json()["code"] == 0

    def test_analysis_with_risk_metrics(self, client):
        """测试分析 API 多个端点联动。"""
        mock_analyzer = MagicMock()

        # 净值走势分析
        mock_analyzer.analyze_nav_trend.return_value = {
            "cumulative_return": 10.5,
            "annualized_return": 5.2,
            "trend": "上升",
        }
        # 风险指标计算
        mock_analyzer.calculate_risk_metrics.return_value = {
            "sharpe_ratio": 1.5,
            "max_drawdown": -8.3,
            "volatility": 15.2,
        }
        app.dependency_overrides[get_analyzer] = lambda: mock_analyzer

        # 调用净值走势分析
        nav_resp = client.post("/api/v1/analysis/nav-trend", json={"symbol": "510300"})
        assert nav_resp.json()["code"] == 0
        assert nav_resp.json()["data"]["cumulative_return"] == 10.5

        # 调用风险指标计算
        risk_resp = client.post("/api/v1/analysis/risk-metrics", json={"symbol": "510300"})
        assert risk_resp.json()["code"] == 0
        assert risk_resp.json()["data"]["sharpe_ratio"] == 1.5

    def test_chart_with_analysis_integration(self, client, tmp_path):
        """测试图表生成与分析模块的联动。"""
        mock_analyzer = MagicMock()
        mock_visualizer = MagicMock()

        # 模拟行业分布分析结果
        mock_analyzer.analyze_industry_distribution.return_value = {
            "industry_distribution": MagicMock(),
        }

        app.dependency_overrides[get_analyzer] = lambda: mock_analyzer
        app.dependency_overrides[get_visualizer] = lambda: mock_visualizer

        with patch("api.routers.chart.CHART_DIR", str(tmp_path)):
            response = client.post("/api/v1/chart/generate", json={
                "symbol": "510300",
                "chart_type": "industry_pie",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        mock_analyzer.analyze_industry_distribution.assert_called_once_with("510300")
        mock_visualizer.plot_industry_pie.assert_called_once()
