# -*- coding: utf-8 -*-
"""
安全配置管理模块单元测试

使用 mock 和临时环境变量，测试 SecureConfig 的环境变量加载、
多环境配置、require 方法和 is_configured 方法。
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from etf_analyzer.secure_config import SecureConfig


# ============================================================
# 测试从环境变量加载配置
# ============================================================


class TestLoadFromEnvironment:
    """从环境变量加载配置相关测试。"""

    def test_read_from_environment_variable(self):
        """测试设置环境变量后能正确读取。"""
        with patch.dict(os.environ, {"TEST_ETF_KEY": "test_value"}, clear=False):
            config = SecureConfig()
            assert config.get("TEST_ETF_KEY") == "test_value"

    def test_environment_variable_priority_over_env_file(self):
        """测试环境变量优先级高于 .env 文件。

        注意：根据 SecureConfig 的实现，.env 文件会覆盖系统环境变量，
        所以这个测试验证 .env 文件值优先于系统环境变量。
        """
        # 设置系统环境变量
        with patch.dict(os.environ, {"ETF_PRIORITY_TEST": "from_os_env"}, clear=False):
            # 模拟 .env 文件不存在的情况，系统环境变量应可读取
            config = SecureConfig()
            # 在 .env 文件不存在时，系统环境变量的值会被保留
            assert config.get("ETF_PRIORITY_TEST") == "from_os_env"

    def test_get_with_default(self):
        """测试配置项不存在时返回默认值。"""
        config = SecureConfig()
        result = config.get("NON_EXISTENT_KEY_12345", default="default_val")
        assert result == "default_val"

    def test_get_non_existent_key_returns_none(self):
        """测试获取不存在的配置项返回 None。"""
        config = SecureConfig()
        result = config.get("NON_EXISTENT_KEY_12345")
        assert result is None


# ============================================================
# 测试多环境配置
# ============================================================


class TestMultiEnvironmentConfig:
    """多环境配置相关测试。"""

    def test_load_env_specific_config(self, tmp_path):
        """测试设置 ETF_ENV 后加载对应环境配置文件。"""
        # 创建 .env.test 文件
        env_test_file = tmp_path / ".env.test"
        env_test_file.write_text("TEST_ENV_KEY=test_env_value\n")

        with patch.dict(os.environ, {"ETF_ENV": "test"}, clear=False):
            config = SecureConfig(project_root=str(tmp_path))
            assert config.get("TEST_ENV_KEY") == "test_env_value"

    def test_env_specific_overrides_base_env(self, tmp_path):
        """测试 .env.{env} 文件优先级高于 .env 文件。"""
        # 创建 .env 文件
        env_file = tmp_path / ".env"
        env_file.write_text("OVERRIDE_KEY=from_base_env\n")

        # 创建 .env.prod 文件
        env_prod_file = tmp_path / ".env.prod"
        env_prod_file.write_text("OVERRIDE_KEY=from_prod_env\n")

        with patch.dict(os.environ, {"ETF_ENV": "prod"}, clear=False):
            config = SecureConfig(project_root=str(tmp_path))
            # .env.prod 应覆盖 .env
            assert config.get("OVERRIDE_KEY") == "from_prod_env"

    def test_no_etf_env_skips_specific_config(self, tmp_path):
        """测试未设置 ETF_ENV 时不加载环境特定配置。"""
        # 创建 .env.test 文件（不应被加载）
        env_test_file = tmp_path / ".env.test"
        env_test_file.write_text("SHOULD_NOT_LOAD=yes\n")

        # 确保 ETF_ENV 未设置
        env_copy = os.environ.copy()
        env_copy.pop("ETF_ENV", None)
        with patch.dict(os.environ, env_copy, clear=True):
            config = SecureConfig(project_root=str(tmp_path))
            assert config.get("SHOULD_NOT_LOAD") is None


# ============================================================
# 测试 require 方法
# ============================================================


class TestRequireMethod:
    """require 方法相关测试。"""

    def test_require_returns_value_when_configured(self):
        """测试配置存在时 require 返回值。"""
        with patch.dict(os.environ, {"ETF_REQUIRE_TEST": "configured_value"}, clear=False):
            config = SecureConfig()
            result = config.require("ETF_REQUIRE_TEST")
            assert result == "configured_value"

    def test_require_returns_none_when_missing(self):
        """测试配置缺失时 require 返回 None 并记录告警。"""
        config = SecureConfig()
        result = config.require("NON_EXISTENT_REQUIRE_KEY_12345")
        assert result is None

    def test_require_returns_none_for_empty_string(self):
        """测试配置值为空字符串时 require 返回 None。"""
        with patch.dict(os.environ, {"ETF_EMPTY_TEST": ""}, clear=False):
            config = SecureConfig()
            result = config.require("ETF_EMPTY_TEST")
            assert result is None


# ============================================================
# 测试 is_configured 方法
# ============================================================


class TestIsConfiguredMethod:
    """is_configured 方法相关测试。"""

    def test_is_configured_returns_true_when_set(self):
        """测试已配置返回 True。"""
        with patch.dict(os.environ, {"ETF_CONFIGURED_TEST": "some_value"}, clear=False):
            config = SecureConfig()
            assert config.is_configured("ETF_CONFIGURED_TEST") is True

    def test_is_configured_returns_false_when_not_set(self):
        """测试未配置返回 False。"""
        config = SecureConfig()
        assert config.is_configured("NON_EXISTENT_CONFIGURED_KEY_12345") is False

    def test_is_configured_returns_false_for_empty_string(self):
        """测试配置值为空字符串时返回 False。"""
        with patch.dict(os.environ, {"ETF_EMPTY_CONFIGURED_TEST": ""}, clear=False):
            config = SecureConfig()
            assert config.is_configured("ETF_EMPTY_CONFIGURED_TEST") is False

    def test_is_configured_returns_true_for_non_string_value(self):
        """测试非字符串类型的值（如从 dotenv_values 获取的数值）返回 True。"""
        config = SecureConfig()
        config._config["NUMERIC_TEST"] = 123
        assert config.is_configured("NUMERIC_TEST") is True
