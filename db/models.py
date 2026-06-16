# -*- coding: utf-8 -*-
"""
数据库模型定义

定义 ETF 基础信息表和历史数据缓存表的 SQLAlchemy ORM 模型。
"""

from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class ETFInfo(Base):
    """ETF 基础信息表"""
    __tablename__ = "etf_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, comment="ETF代码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="ETF名称")
    etf_type: Mapped[str] = mapped_column(String(50), default="", comment="ETF类型")
    listing_date: Mapped[str] = mapped_column(String(20), default="", comment="上市日期")
    management_fee: Mapped[float] = mapped_column(Float, default=0.0, comment="管理费率")
    custody_fee: Mapped[float] = mapped_column(Float, default=0.0, comment="托管费率")
    scale: Mapped[float] = mapped_column(Float, default=0.0, comment="基金规模(亿元)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<ETFInfo(symbol={self.symbol}, name={self.name})>"


class HistoryDataCache(Base):
    """历史数据缓存表"""
    __tablename__ = "history_data_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, comment="ETF代码")
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, comment="交易日期(YYYY-MM-DD)")
    open: Mapped[float] = mapped_column(Float, default=0.0, comment="开盘价")
    close: Mapped[float] = mapped_column(Float, default=0.0, comment="收盘价")
    high: Mapped[float] = mapped_column(Float, default=0.0, comment="最高价")
    low: Mapped[float] = mapped_column(Float, default=0.0, comment="最低价")
    volume: Mapped[float] = mapped_column(Float, default=0.0, comment="成交量")
    amount: Mapped[float] = mapped_column(Float, default=0.0, comment="成交额")
    change_pct: Mapped[float] = mapped_column(Float, default=0.0, comment="涨跌幅")
    change_amt: Mapped[float] = mapped_column(Float, default=0.0, comment="涨跌额")
    turnover_rate: Mapped[float] = mapped_column(Float, default=0.0, comment="换手率")
    data_source: Mapped[str] = mapped_column(String(20), default="", comment="数据来源")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_symbol_date", "symbol", "trade_date", unique=True),
        Index("idx_symbol", "symbol"),
    )

    def __repr__(self):
        return f"<HistoryDataCache(symbol={self.symbol}, date={self.trade_date})>"
