# -*- coding: utf-8 -*-
"""
ETF分析器重试与速率限制工具模块

提供两个核心工具：
1. retry 装饰器：带随机抖动（jitter）的指数退避重试，专门针对网络相关异常。
2. RateLimiter 类：全局速率限制器，防止高频请求触发 API 服务端的 IP 封禁。
"""

import random
import time
import threading
import functools
import logging

import requests
import urllib3.exceptions

logger = logging.getLogger("retry")


class RateLimiter:
    """全局速率限制器，控制对远程 API 的请求频率。

    通过记录上次请求时间戳，确保相邻请求之间的间隔不低于 min_interval 秒。
    支持连续失败检测：当连续失败次数增多时自动降低请求频率。

    Attributes:
        min_interval: 相邻请求最小间隔（秒）。
        _last_call_time: 上次请求的时间戳。
        _lock: 线程锁，保证多线程安全。
        consecutive_failures: 连续失败次数计数器。
    """

    def __init__(self, min_interval=1.5):
        """初始化速率限制器。

        Args:
            min_interval: 相邻请求最小间隔（秒），默认 1.5 秒。
        """
        self.min_interval = min_interval
        self._last_call_time = 0.0
        self._lock = threading.Lock()
        self.consecutive_failures = 0

    def acquire(self):
        """获取请求许可，必要时阻塞等待。

        如果距离上次请求不足 min_interval 秒，则 sleep 剩余时间。
        当连续失败次数 >= 2 时，自动将间隔提升至 3 秒。
        当连续失败次数 >= 3 时，额外建议用户等待。
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call_time

            # 根据连续失败次数动态调整间隔
            effective_interval = self.min_interval
            if self.consecutive_failures >= 2:
                effective_interval = max(self.min_interval, 3.0)

            if elapsed < effective_interval:
                sleep_time = effective_interval - elapsed
                logger.debug(
                    "速率限制：等待 %.2f 秒（连续失败 %d 次）",
                    sleep_time, self.consecutive_failures,
                )
                time.sleep(sleep_time)

            self._last_call_time = time.time()

    def report_success(self):
        """报告一次成功的请求，重置连续失败计数器。"""
        with self._lock:
            self.consecutive_failures = 0

    def report_failure(self):
        """报告一次失败的请求，递增连续失败计数器。"""
        with self._lock:
            self.consecutive_failures += 1
            if self.consecutive_failures >= 3:
                logger.warning(
                    "连续 %d 次请求失败，建议稍后再试或检查网络连接",
                    self.consecutive_failures,
                )


# 全局单例速率限制器，所有模块共享同一个实例
rate_limiter = RateLimiter(min_interval=1.5)


# 可重试的网络异常元组
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    urllib3.exceptions.ProtocolError,
)


def retry(
    max_attempts=3,
    base_delay=2.0,
    max_delay=60.0,
    jitter=0.5,
    retryable_exceptions=RETRYABLE_EXCEPTIONS,
):
    """带随机抖动指数退避的重试装饰器。

    专用于网络请求场景，捕获连接中断、超时、协议错误等瞬时异常，
    并在重试间隔中加入随机化以避免触发 API 反爬机制。

    Args:
        max_attempts: 最大重试次数（包括首次尝试），默认 3 次。
        base_delay: 基础等待时间（秒），默认 2.0 秒。
        max_delay: 最大等待时间（秒），默认 60.0 秒。
        jitter: 随机抖动因子，0~1 之间。0.5 表示实际等待时间在
            50%~150% 范围内随机波动，默认 0.5。
        retryable_exceptions: 可重试的异常元组，默认包含
            ConnectionError、Timeout、ProtocolError。

    Returns:
        装饰后的函数，成功时返回原函数结果，所有重试耗尽后抛出最后一次异常。

    Usage:
        @retry(max_attempts=3, base_delay=2.0)
        def fetch_data():
            return ak.fund_etf_spot_em()
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    # 调用成功，通知速率限制器
                    rate_limiter.report_success()
                    return result
                except retryable_exceptions as e:
                    last_exception = e
                    rate_limiter.report_failure()
                    if attempt < max_attempts:
                        # 计算指数退避时间
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        # 加入随机抖动，避免多个重试对齐
                        actual_delay = delay * random.uniform(1 - jitter, 1 + jitter)
                        logger.warning(
                            "请求失败（尝试 %d/%d）：%s，%.2f 秒后重试",
                            attempt, max_attempts, e, actual_delay,
                        )
                        time.sleep(actual_delay)
                    else:
                        logger.error(
                            "请求失败（尝试 %d/%d）：%s，重试已耗尽",
                            attempt, max_attempts, e,
                        )
                except Exception as e:
                    # 非重试范围内的异常直接抛出
                    logger.debug("非重试异常：%s", e)
                    raise
            # 所有重试耗尽，重新抛出最后一次异常
            raise last_exception
        return wrapper
    return decorator