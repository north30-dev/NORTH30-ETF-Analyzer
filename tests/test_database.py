# -*- coding: utf-8 -*-
"""数据库持久化层单元测试"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, init_db
from db.models import ETFInfo, HistoryDataCache
from db.crud import (
    get_etf_info, get_etf_info_list, create_etf_info, upsert_etf_info,
    bulk_upsert_etf_info, get_history_data, get_latest_trade_date,
    bulk_insert_history_data, delete_history_data,
)


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


class TestETFInfoModel:
    """ETFInfo 模型测试"""

    def test_create_etf_info(self, db_session):
        etf = ETFInfo(symbol="510300", name="沪深300ETF")
        db_session.add(etf)
        db_session.commit()
        assert etf.id is not None
        assert etf.symbol == "510300"
        assert etf.name == "沪深300ETF"

    def test_etf_info_repr(self, db_session):
        etf = ETFInfo(symbol="510300", name="沪深300ETF")
        assert "510300" in repr(etf)


class TestHistoryDataCacheModel:
    """HistoryDataCache 模型测试"""

    def test_create_history_data(self, db_session):
        data = HistoryDataCache(
            symbol="510300", trade_date="2024-01-02",
            open=3.5, close=3.6, high=3.7, low=3.4,
            volume=1000000, amount=3500000,
        )
        db_session.add(data)
        db_session.commit()
        assert data.id is not None
        assert data.symbol == "510300"


class TestETFCRUD:
    """ETF 信息 CRUD 测试"""

    def test_create_and_get_etf_info(self, db_session):
        etf = create_etf_info(db_session, "510300", "沪深300ETF")
        assert etf.symbol == "510300"
        result = get_etf_info(db_session, "510300")
        assert result is not None
        assert result.name == "沪深300ETF"

    def test_get_etf_info_not_found(self, db_session):
        result = get_etf_info(db_session, "999999")
        assert result is None

    def test_get_etf_info_list(self, db_session):
        create_etf_info(db_session, "510300", "沪深300ETF")
        create_etf_info(db_session, "510500", "中证500ETF")
        result = get_etf_info_list(db_session)
        assert len(result) == 2

    def test_get_etf_info_list_with_keyword(self, db_session):
        create_etf_info(db_session, "510300", "沪深300ETF")
        create_etf_info(db_session, "510500", "中证500ETF")
        result = get_etf_info_list(db_session, keyword="沪深")
        assert len(result) == 1

    def test_upsert_etf_info_create(self, db_session):
        etf = upsert_etf_info(db_session, "510300", "沪深300ETF", scale=100.0)
        assert etf.symbol == "510300"
        assert etf.scale == 100.0

    def test_upsert_etf_info_update(self, db_session):
        create_etf_info(db_session, "510300", "沪深300ETF", scale=100.0)
        etf = upsert_etf_info(db_session, "510300", "沪深300ETF更新", scale=200.0)
        assert etf.name == "沪深300ETF更新"
        assert etf.scale == 200.0

    def test_bulk_upsert_etf_info(self, db_session):
        etf_list = [
            {"symbol": "510300", "name": "沪深300ETF"},
            {"symbol": "510500", "name": "中证500ETF"},
        ]
        count = bulk_upsert_etf_info(db_session, etf_list)
        assert count == 2


class TestHistoryDataCRUD:
    """历史数据 CRUD 测试"""

    def test_insert_and_get_history_data(self, db_session):
        bulk_insert_history_data(db_session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-03", "close": 3.6},
        ])
        result = get_history_data(db_session, "510300")
        assert len(result) == 2

    def test_get_history_data_with_date_range(self, db_session):
        bulk_insert_history_data(db_session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-03", "close": 3.6},
            {"symbol": "510300", "trade_date": "2024-01-04", "close": 3.7},
        ])
        result = get_history_data(db_session, "510300", start_date="2024-01-03")
        assert len(result) == 2

    def test_get_latest_trade_date(self, db_session):
        bulk_insert_history_data(db_session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-05", "close": 3.6},
        ])
        result = get_latest_trade_date(db_session, "510300")
        assert result == "2024-01-05"

    def test_get_latest_trade_date_no_data(self, db_session):
        result = get_latest_trade_date(db_session, "999999")
        assert result is None

    def test_delete_history_data(self, db_session):
        bulk_insert_history_data(db_session, [
            {"symbol": "510300", "trade_date": "2024-01-02", "close": 3.5},
            {"symbol": "510300", "trade_date": "2024-01-03", "close": 3.6},
        ])
        count = delete_history_data(db_session, "510300")
        assert count == 2
        result = get_history_data(db_session, "510300")
        assert len(result) == 0
