# -*- coding: utf-8 -*-
"""统一配置管理系统单元测试"""

import os
from pathlib import Path

import pytest

from config.settings import Settings, get_settings, reset_settings


@pytest.fixture(autouse=True)
def clean_settings():
    """每个测试前后重置全局配置单例。"""
    reset_settings()
    yield
    reset_settings()


class TestSettings:
    """Settings 类测试"""

    def test_default_settings(self):
        """测试默认配置加载。"""
        settings = get_settings()
        assert settings.server.host == "0.0.0.0"
        assert settings.server.port == 8000
        assert settings.cache.expire_hours == 4
        assert settings.analysis.risk_free_rate == 0.02
        assert settings.report.font == "SimHei"

    def test_singleton(self):
        """测试全局单例。"""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_yaml_loading(self):
        """测试 YAML 配置文件加载。"""
        settings = get_settings()
        # default.yaml 应该被加载
        assert settings.server.api_prefix == "/api/v1"
        assert settings.database.driver == "mysql+pymysql"

    def test_env_override(self, monkeypatch):
        """测试环境变量覆盖。"""
        monkeypatch.setenv("SERVER_PORT", "9000")
        monkeypatch.setenv("DB_HOST", "192.168.1.100")
        reset_settings()
        settings = get_settings()
        assert settings.server.port == 9000
        assert settings.database.host == "192.168.1.100"

    def test_database_url(self):
        """测试数据库 URL 构建。"""
        settings = get_settings()
        url = settings.database.url
        assert "mysql+pymysql" in url
        assert "127.0.0.1" in url
        assert "3306" in url

    def test_redis_url(self):
        """测试 Redis URL 构建。"""
        settings = get_settings()
        url = settings.redis.url
        assert "redis://" in url
        assert "6379" in url

    def test_ensure_dirs(self, tmp_path):
        """测试目录创建。"""
        settings = Settings()
        settings.project_root = tmp_path
        settings._init_paths()
        settings.ensure_dirs()
        assert settings.cache_dir_path.exists()
        assert settings.log_dir_path.exists()
        assert settings.report_dir_path.exists()

    def test_industry_maps(self):
        """测试行业分类映射。"""
        settings = get_settings()
        assert "801780" in settings.sw_industry_map
        assert settings.sw_industry_map["801780"] == "银行"
        assert "CI005001" in settings.zx_industry_map
        assert settings.zx_industry_map["CI005001"] == "石油石化"

    def test_datasource_priority(self):
        """测试数据源优先级配置。"""
        settings = get_settings()
        assert settings.datasource.priority == [
            "akshare",
            "tushare",
            "baostock",
            "pytdx",
        ]

    def test_deep_merge(self):
        """测试深度合并。"""
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 99}, "e": 5}
        result = Settings._deep_merge(base, override)
        assert result == {"a": 1, "b": {"c": 99, "d": 3}, "e": 5}
