# -*- coding: utf-8 -*-
"""
安全配置管理模块

支持从 .env 文件、环境特定配置文件和系统环境变量加载配置，
并提供统一的配置访问接口。加载优先级：.env.{env} > .env > 系统环境变量。
"""

import logging
import os
from dotenv import dotenv_values

# 使用标准 logging，避免与 config.py 产生循环导入
# 当 logger 模块初始化完成后，同名 logger 会自动获得已配置的 handler
logger = logging.getLogger("etf_analyzer.secure_config")

# 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SecureConfig:
    """安全配置管理类。

    负责从多个来源加载配置，并按照优先级合并：
    1. .env.{env} 文件（最高优先级）
    2. .env 文件
    3. 系统环境变量（最低优先级）

    通过 ETF_ENV 环境变量决定加载哪个环境特定配置文件，
    可选值为 dev、test、prod。
    """

    def __init__(self, project_root=None):
        """初始化 SecureConfig 实例。

        Args:
            project_root: 项目根目录路径，默认为本模块所在目录的上级目录。
        """
        self._project_root = project_root or _PROJECT_ROOT
        self._config = {}
        self._load()

    def _load(self):
        """从各配置源加载并合并配置。"""
        # 第一层：系统环境变量（最低优先级）
        self._config.update(os.environ)

        # 第二层：.env 文件（覆盖系统环境变量）
        env_path = os.path.join(self._project_root, ".env")
        if os.path.exists(env_path):
            env_values = dotenv_values(env_path)
            self._config.update({k: v for k, v in env_values.items() if v is not None})
            logger.info("已加载 .env 配置文件")

        # 第三层：.env.{env} 文件（最高优先级，覆盖 .env 和系统环境变量）
        env_name = os.environ.get("ETF_ENV", "").strip()
        if env_name:
            env_specific_path = os.path.join(self._project_root, f".env.{env_name}")
            if os.path.exists(env_specific_path):
                env_specific_values = dotenv_values(env_specific_path)
                self._config.update(
                    {k: v for k, v in env_specific_values.items() if v is not None}
                )
                logger.info("已加载 .env.%s 配置文件", env_name)
            else:
                logger.warning("ETF_ENV=%s，但未找到 .env.%s 配置文件", env_name, env_name)

    def get(self, key, default=None):
        """获取配置值。

        Args:
            key: 配置项键名。
            default: 配置项不存在时的默认返回值，默认为 None。

        Returns:
            配置项的值，如果不存在则返回 default。
        """
        value = self._config.get(key)
        if value is not None:
            return value
        return default

    def require(self, key):
        """获取必需配置项的值。

        当配置项缺失时，记录 WARNING 日志并返回 None，
        而不是抛出异常导致程序崩溃。

        Args:
            key: 配置项键名。

        Returns:
            配置项的值，如果缺失则返回 None。
        """
        value = self._config.get(key)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            logger.warning("必需配置项 '%s' 未配置", key)
            return None
        return value

    def is_configured(self, key):
        """检查某个配置项是否已配置。

        配置项存在且值非空字符串时视为已配置。

        Args:
            key: 配置项键名。

        Returns:
            bool: 配置项是否已配置。
        """
        value = self._config.get(key)
        return value is not None and (not isinstance(value, str) or value.strip() != "")


# 模块级全局实例，供其他模块直接使用
secure_config = SecureConfig()
