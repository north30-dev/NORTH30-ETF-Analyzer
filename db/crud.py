# -*- coding: utf-8 -*-
"""
数据库 CRUD 操作

提供 ETF 基础信息表和历史数据缓存表的增删改查操作。
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import ETFInfo, HistoryDataCache


# ==================== ETF 基础信息 CRUD ====================

def get_etf_info(db: Session, symbol: str) -> Optional[ETFInfo]:
    """根据代码查询 ETF 基础信息。"""
    return db.query(ETFInfo).filter(ETFInfo.symbol == symbol).first()


def get_etf_info_list(db: Session, keyword: Optional[str] = None,
                      skip: int = 0, limit: int = 100) -> List[ETFInfo]:
    """查询 ETF 列表，支持关键词搜索和分页。"""
    query = db.query(ETFInfo)
    if keyword:
        query = query.filter(
            (ETFInfo.symbol.contains(keyword)) | (ETFInfo.name.contains(keyword))
        )
    return query.offset(skip).limit(limit).all()


def create_etf_info(db: Session, symbol: str, name: str, **kwargs) -> ETFInfo:
    """创建 ETF 基础信息记录。"""
    etf_info = ETFInfo(symbol=symbol, name=name, **kwargs)
    db.add(etf_info)
    db.commit()
    db.refresh(etf_info)
    return etf_info


def upsert_etf_info(db: Session, symbol: str, name: str, **kwargs) -> ETFInfo:
    """插入或更新 ETF 基础信息记录。"""
    existing = get_etf_info(db, symbol)
    if existing:
        for key, value in kwargs.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        existing.name = name
        db.commit()
        db.refresh(existing)
        return existing
    return create_etf_info(db, symbol, name, **kwargs)


def bulk_upsert_etf_info(db: Session, etf_list: list) -> int:
    """批量插入或更新 ETF 基础信息。

    Args:
        etf_list: 包含 ETF 信息的字典列表，每个字典需包含 symbol 和 name。

    Returns:
        处理的记录数。
    """
    count = 0
    for item in etf_list:
        symbol = item.get("symbol", "")
        name = item.get("name", "")
        if not symbol or not name:
            continue
        kwargs = {k: v for k, v in item.items() if k not in ("symbol", "name")}
        upsert_etf_info(db, symbol, name, **kwargs)
        count += 1
    return count


# ==================== 历史数据缓存 CRUD ====================

def get_history_data(db: Session, symbol: str, start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> List[HistoryDataCache]:
    """查询历史数据缓存。"""
    query = db.query(HistoryDataCache).filter(HistoryDataCache.symbol == symbol)
    if start_date:
        query = query.filter(HistoryDataCache.trade_date >= start_date)
    if end_date:
        query = query.filter(HistoryDataCache.trade_date <= end_date)
    return query.order_by(HistoryDataCache.trade_date).all()


def get_latest_trade_date(db: Session, symbol: str) -> Optional[str]:
    """获取某 ETF 最新缓存的交易日期。"""
    result = (db.query(HistoryDataCache.trade_date)
              .filter(HistoryDataCache.symbol == symbol)
              .order_by(HistoryDataCache.trade_date.desc())
              .first())
    return result[0] if result else None


def bulk_insert_history_data(db: Session, data_list: list) -> int:
    """批量插入历史数据缓存。

    Args:
        data_list: 包含历史数据的字典列表。

    Returns:
        插入的记录数。
    """
    objects = [HistoryDataCache(**item) for item in data_list]
    db.bulk_save_objects(objects)
    db.commit()
    return len(objects)


def delete_history_data(db: Session, symbol: str,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> int:
    """删除历史数据缓存。"""
    query = db.query(HistoryDataCache).filter(HistoryDataCache.symbol == symbol)
    if start_date:
        query = query.filter(HistoryDataCache.trade_date >= start_date)
    if end_date:
        query = query.filter(HistoryDataCache.trade_date <= end_date)
    count = query.count()
    query.delete()
    db.commit()
    return count
