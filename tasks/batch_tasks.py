# -*- coding: utf-8 -*-
"""
批量分析任务

提供 Celery 异步任务，支持多 ETF 批量分析。
"""

from tasks.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.batch_tasks.batch_analyze")
def batch_analyze(self, symbols: list, start_date: str = None,
                  end_date: str = None):
    """批量分析多个 ETF。

    Args:
        symbols: ETF 代码列表。
        start_date: 起始日期。
        end_date: 结束日期。

    Returns:
        dict: 包含各 ETF 分析结果的字典。
    """
    from etf_analyzer.core.analyzer import ETFAnalyzer

    analyzer = ETFAnalyzer()
    results = {}
    total = len(symbols)

    for i, symbol in enumerate(symbols):
        self.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": total, "status": f"分析 {symbol}"},
        )
        try:
            nav_result = analyzer.analyze_nav_trend(
                symbol, start_date=start_date, end_date=end_date,
            )
            risk_result = analyzer.calculate_risk_metrics(
                symbol, start_date=start_date, end_date=end_date,
            )
            results[symbol] = {
                "status": "SUCCESS",
                "nav_trend": {
                    k: v for k, v in (nav_result or {}).items()
                    if k != "nav_data"
                },
                "risk_metrics": risk_result,
            }
        except Exception as e:
            results[symbol] = {"status": "FAILURE", "error": str(e)}

    return results
