# -*- coding: utf-8 -*-
"""
异步报告生成任务

提供 Celery 异步任务，在后台生成 ETF 分析报告。
"""

from tasks.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.report_tasks.generate_report")
def generate_report(self, symbol: str, start_date: str = None,
                    end_date: str = None, benchmark_symbol: str = None,
                    modules: list = None):
    """异步生成 ETF 分析报告。

    Args:
        symbol: ETF 代码。
        start_date: 起始日期。
        end_date: 结束日期。
        benchmark_symbol: 基准指数代码。
        modules: 报告模块列表。

    Returns:
        dict: 包含 output_path 和 status 的字典。
    """
    self.update_state(state="PROGRESS", meta={"current": 0, "total": 5, "status": "初始化"})

    try:
        from etf_analyzer.core.data_fetcher import ETFDataFetcher
        from etf_analyzer.core.analyzer import ETFAnalyzer
        from etf_analyzer.core.report_generator import ReportGenerator

        fetcher = ETFDataFetcher()
        analyzer = ETFAnalyzer()
        report_gen = ReportGenerator()

        # 收集分析数据
        results = {}

        self.update_state(state="PROGRESS", meta={"current": 1, "total": 5, "status": "净值走势分析"})
        nav_result = analyzer.analyze_nav_trend(
            symbol, start_date=start_date, end_date=end_date,
        )
        if nav_result:
            results["nav_data"] = nav_result.get("nav_data")
            results["performance_metrics"] = {
                "cumulative_return": nav_result.get("cumulative_return"),
                "annualized_return": nav_result.get("annualized_return"),
            }

        self.update_state(state="PROGRESS", meta={"current": 2, "total": 5, "status": "成分股分析"})
        holdings_result = analyzer.analyze_holdings(symbol)
        if holdings_result:
            results["holdings_data"] = holdings_result.get("top10_holdings")

        self.update_state(state="PROGRESS", meta={"current": 3, "total": 5, "status": "行业分布统计"})
        industry_result = analyzer.analyze_industry_distribution(symbol)
        if industry_result:
            results["industry_data"] = industry_result.get("industry_distribution")

        self.update_state(state="PROGRESS", meta={"current": 4, "total": 5, "status": "风险指标计算"})
        risk_result = analyzer.calculate_risk_metrics(
            symbol, start_date=start_date, end_date=end_date,
            benchmark_symbol=benchmark_symbol,
        )
        if risk_result:
            results["risk_metrics"] = risk_result

        if not results:
            return {"status": "FAILURE", "message": "未能收集到分析数据"}

        self.update_state(state="PROGRESS", meta={"current": 5, "total": 5, "status": "生成报告"})
        output_path = report_gen.generate_report(symbol, results, modules=modules)

        return {"status": "SUCCESS", "output_path": output_path}

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise
