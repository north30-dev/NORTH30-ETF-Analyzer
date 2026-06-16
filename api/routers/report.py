# -*- coding: utf-8 -*-
"""报告生成 API 路由"""

from celery.result import AsyncResult
from fastapi import APIRouter

from api.schemas.etf import APIResponse
from api.schemas.report import ReportGenerateRequest, ReportTaskResponse
from tasks.celery_app import celery_app
from tasks.report_tasks import generate_report

router = APIRouter(prefix="/report", tags=["报告生成"])


@router.post("/generate", summary="生成分析报告（异步）")
def generate_report_endpoint(
    request: ReportGenerateRequest,
):
    """异步生成分析报告，返回 Celery 任务 ID。"""
    try:
        result = generate_report.delay(
            request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            benchmark_symbol=request.benchmark_symbol,
            modules=request.modules,
        )
        return APIResponse(code=0, data={"task_id": result.id, "status": "PENDING"})
    except Exception as e:
        return APIResponse(code=500, message=f"任务创建失败: {str(e)}")


@router.get("/task/{task_id}", summary="查询报告任务状态")
def get_report_task_status(task_id: str):
    """查询异步报告生成任务的状态。"""
    result = AsyncResult(task_id, app=celery_app)

    if result.status == "PENDING":
        return APIResponse(code=0, data={"task_id": task_id, "status": "PENDING"})
    elif result.status == "STARTED":
        return APIResponse(code=0, data={"task_id": task_id, "status": "STARTED", "result": result.info})
    elif result.status == "PROGRESS":
        return APIResponse(code=0, data={"task_id": task_id, "status": "PROGRESS", "result": result.info})
    elif result.status == "SUCCESS":
        return APIResponse(code=0, data={"task_id": task_id, "status": "SUCCESS", "result": result.result})
    elif result.status == "FAILURE":
        return APIResponse(code=0, data={"task_id": task_id, "status": "FAILURE", "result": str(result.result)})
    else:
        return APIResponse(code=0, data={"task_id": task_id, "status": result.status, "result": result.info})
