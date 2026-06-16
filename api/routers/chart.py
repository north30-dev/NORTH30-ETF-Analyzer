# -*- coding: utf-8 -*-
"""图表生成 API 路由"""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from api.deps import get_fetcher, get_analyzer, get_visualizer
from api.schemas.etf import APIResponse
from api.schemas.report import ChartGenerateRequest
from etf_analyzer.core.data_fetcher import ETFDataFetcher
from etf_analyzer.core.analyzer import ETFAnalyzer
from etf_analyzer.core.visualizer import ETFVisualizer
from config import REPORT_DIR_PATH

router = APIRouter(prefix="/chart", tags=["图表生成"])

# 图表文件存储目录
CHART_DIR = os.path.join(REPORT_DIR_PATH, "charts")


@router.post("/generate", summary="生成图表")
def generate_chart(
    request: ChartGenerateRequest,
    fetcher: ETFDataFetcher = Depends(get_fetcher),
    analyzer: ETFAnalyzer = Depends(get_analyzer),
    visualizer: ETFVisualizer = Depends(get_visualizer),
):
    """生成指定类型的图表，返回图片 URL。"""
    os.makedirs(CHART_DIR, exist_ok=True)
    chart_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{request.symbol}_{request.chart_type}_{timestamp}_{chart_id}.png"
    save_path = os.path.join(CHART_DIR, filename)

    chart_type = request.chart_type
    try:
        if chart_type == "kline":
            df = fetcher.get_history_data(
                request.symbol, start_date=request.start_date, end_date=request.end_date,
            )
            if df is None or df.empty:
                return APIResponse(code=404, message="未获取到历史数据")
            visualizer.plot_kline(df, symbol=request.symbol, save_path=save_path, show=False)

        elif chart_type == "nav_trend":
            result = analyzer.analyze_nav_trend(
                request.symbol, start_date=request.start_date, end_date=request.end_date,
            )
            if not result or result.get("nav_data") is None:
                return APIResponse(code=404, message="净值走势分析失败")
            visualizer.plot_nav_trend(
                result["nav_data"], symbol=request.symbol, save_path=save_path, show=False,
            )

        elif chart_type == "industry_pie":
            result = analyzer.analyze_industry_distribution(request.symbol)
            if not result or result.get("industry_distribution") is None:
                return APIResponse(code=404, message="行业分布统计失败")
            visualizer.plot_industry_pie(
                result["industry_distribution"], symbol=request.symbol, save_path=save_path, show=False,
            )

        elif chart_type == "holdings_bar":
            result = analyzer.analyze_holdings(request.symbol)
            if not result or result.get("top10_holdings") is None:
                return APIResponse(code=404, message="成分股分析失败")
            visualizer.plot_holdings_bar(
                result["top10_holdings"], symbol=request.symbol, save_path=save_path, show=False,
            )

        elif chart_type == "drawdown":
            df = fetcher.get_history_data(
                request.symbol, start_date=request.start_date, end_date=request.end_date,
            )
            if df is None or df.empty:
                return APIResponse(code=404, message="未获取到历史数据")
            visualizer.plot_drawdown(df, symbol=request.symbol, save_path=save_path, show=False)

        else:
            return APIResponse(code=400, message=f"不支持的图表类型: {chart_type}")

        chart_url = f"/charts/{filename}"
        return APIResponse(code=0, data={"url": chart_url, "filename": filename})

    except Exception as e:
        return APIResponse(code=500, message=f"图表生成失败: {str(e)}")
