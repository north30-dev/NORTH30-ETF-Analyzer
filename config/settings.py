# -*- coding: utf-8 -*-
"""
统一配置管理模块

基于 Pydantic BaseSettings + YAML 配置文件实现统一配置管理。
加载优先级：环境变量 > 环境 YAML > 默认 YAML
敏感信息通过 .env 文件或环境变量提供。
"""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def _load_yaml(path: Path) -> dict:
    """加载 YAML 配置文件。"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ServerSettings(BaseSettings):
    """API 服务配置"""

    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    debug: bool = True

    model_config = {"env_prefix": "SERVER_", "env_file": ".env", "env_file_encoding": "utf-8"}


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    driver: str = "mysql+pymysql"
    host: str = "127.0.0.1"
    port: int = 3306
    name: str = "etf_analyzer"
    user: str = "root"
    password: str = ""
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 3600

    model_config = {"env_prefix": "DB_", "env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def url(self) -> str:
        """构建数据库连接 URL。"""
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}?charset=utf8mb4"


class RedisSettings(BaseSettings):
    """Redis 配置"""

    host: str = "127.0.0.1"
    port: int = 6379
    password: str = ""
    db: int = 0

    model_config = {"env_prefix": "REDIS_", "env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def url(self) -> str:
        """构建 Redis 连接 URL。"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseSettings):
    """Celery 异步任务配置"""

    broker_url: str = "redis://127.0.0.1:6379/1"
    result_backend: str = "redis://127.0.0.1:6379/2"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: List[str] = Field(default_factory=lambda: ["json"])
    timezone: str = "Asia/Shanghai"
    enable_utc: bool = False

    model_config = {"env_prefix": "CELERY_", "env_file": ".env", "env_file_encoding": "utf-8"}


class DatasourceSettings(BaseSettings):
    """数据源配置"""

    priority: List[str] = Field(
        default_factory=lambda: ["akshare", "tushare", "baostock", "pytdx"]
    )
    health_check_interval: int = 300
    failure_threshold: int = 3
    quality_threshold: int = 60
    cross_validation_threshold: float = 1.0
    tushare_token: str = ""
    pytdx_host: str = "119.147.212.81"
    pytdx_port: int = 7709

    model_config = {"env_prefix": "DATASOURCE_", "env_file": ".env", "env_file_encoding": "utf-8"}


class AnalysisSettings(BaseSettings):
    """分析参数配置"""

    default_start_date: str = "20200101"
    risk_free_rate: float = 0.02

    model_config = {"env_prefix": "ANALYSIS_", "env_file": ".env", "env_file_encoding": "utf-8"}


class ReportSettings(BaseSettings):
    """报告配置"""

    output_dir: str = "reports"
    font: str = "SimHei"
    font_size: int = 12
    title_font_size: int = 18
    page_size: str = "A4"

    model_config = {"env_prefix": "REPORT_", "env_file": ".env", "env_file_encoding": "utf-8"}


class CacheSettings(BaseSettings):
    """缓存配置"""

    dir: str = "cache"
    expire_hours: int = 4

    model_config = {"env_prefix": "CACHE_", "env_file": ".env", "env_file_encoding": "utf-8"}


class LoggingSettings(BaseSettings):
    """日志配置"""

    dir: str = "logs"
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = {"env_prefix": "LOGGING_", "env_file": ".env", "env_file_encoding": "utf-8"}


class Settings(BaseSettings):
    """全局统一配置

    从 YAML 配置文件和环境变量加载配置，合并后提供统一访问接口。
    加载优先级：环境变量 > 环境 YAML > 默认 YAML。
    """

    # 项目根目录
    project_root: Path = PROJECT_ROOT

    # 当前运行环境
    env: str = "development"

    # 子配置模块
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    datasource: DatasourceSettings = Field(default_factory=DatasourceSettings)
    analysis: AnalysisSettings = Field(default_factory=AnalysisSettings)
    report: ReportSettings = Field(default_factory=ReportSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # 行业分类映射（不从 YAML 加载，保持硬编码）
    sw_industry_map: dict = Field(default_factory=dict)
    zx_industry_map: dict = Field(default_factory=dict)

    model_config = {"env_prefix": "ETF_", "env_file": ".env", "env_file_encoding": "utf-8"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_yaml_configs()
        self._init_industry_maps()
        self._init_paths()

    def _load_yaml_configs(self):
        """从 YAML 配置文件加载配置，合并到各子配置模块。

        加载优先级：环境变量 > 环境 YAML > 默认 YAML。
        当环境变量存在时，跳过 YAML 中对应字段的值，让 BaseSettings
        自动从环境变量读取。
        """
        # 加载默认配置
        default_config = _load_yaml(self.project_root / "config" / "default.yaml")

        # 加载环境特定配置
        env_name = os.environ.get("ETF_ENV", self.env)
        self.env = env_name
        env_config = _load_yaml(self.project_root / "config" / f"{env_name}.yaml")

        # 合并配置：环境配置覆盖默认配置
        merged = self._deep_merge(default_config, env_config)

        # 配置节 -> (子配置类, 环境变量前缀) 映射
        section_map = {
            "server": (ServerSettings, "SERVER_"),
            "database": (DatabaseSettings, "DB_"),
            "redis": (RedisSettings, "REDIS_"),
            "celery": (CelerySettings, "CELERY_"),
            "datasource": (DatasourceSettings, "DATASOURCE_"),
            "analysis": (AnalysisSettings, "ANALYSIS_"),
            "report": (ReportSettings, "REPORT_"),
            "cache": (CacheSettings, "CACHE_"),
            "logging": (LoggingSettings, "LOGGING_"),
        }

        for section, (settings_cls, env_prefix) in section_map.items():
            if section in merged:
                yaml_values = merged[section]
                # 移除已通过环境变量配置的字段，确保环境变量优先级高于 YAML
                filtered = {}
                for key, value in yaml_values.items():
                    env_key = f"{env_prefix}{key.upper()}"
                    if env_key not in os.environ:
                        filtered[key] = value
                setattr(self, section, settings_cls(**filtered))

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """深度合并两个字典，override 中的值覆盖 base 中的值。"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Settings._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _init_industry_maps(self):
        """初始化行业分类映射。"""
        self.sw_industry_map = {
            "801780": "银行",
            "801790": "非银金融",
            "801180": "房地产",
            "801150": "建筑装饰",
            "801160": "建筑材料",
            "801040": "钢铁",
            "801020": "采掘",
            "801050": "有色金属",
            "801890": "机械设备",
            "801730": "电气设备",
            "801740": "国防军工",
            "801750": "计算机",
            "801770": "通信",
            "801080": "电子",
            "801760": "传媒",
            "801950": "医药生物",
            "801120": "食品饮料",
            "801010": "农林牧渔",
            "801110": "家用电器",
            "801880": "汽车",
            "801200": "商业贸易",
            "801940": "公用事业",
            "801170": "交通运输",
            "801210": "休闲服务",
            "801230": "综合",
            "801030": "化工",
            "801140": "轻工制造",
            "801130": "纺织服装",
        }
        self.zx_industry_map = {
            "CI005001": "石油石化",
            "CI005002": "煤炭",
            "CI005003": "有色金属",
            "CI005004": "电力及公用事业",
            "CI005005": "钢铁",
            "CI005006": "基础化工",
            "CI005007": "建筑",
            "CI005008": "建材",
            "CI005009": "轻工制造",
            "CI005010": "机械",
            "CI005011": "电力设备及新能源",
            "CI005012": "国防军工",
            "CI005013": "汽车",
            "CI005014": "商贸零售",
            "CI005015": "消费者服务",
            "CI005016": "家电",
            "CI005017": "纺织服装",
            "CI005018": "医药",
            "CI005019": "食品饮料",
            "CI005020": "农林牧渔",
            "CI005021": "银行",
            "CI005022": "非银行金融",
            "CI005023": "房地产",
            "CI005024": "交通运输",
            "CI005025": "电子",
            "CI005026": "通信",
            "CI005027": "计算机",
            "CI005028": "传媒",
            "CI005029": "综合金融",
            "CI005030": "综合",
        }

    def _init_paths(self):
        """初始化路径相关属性。"""
        self._cache_dir_path = self.project_root / self.cache.dir
        self._log_dir_path = self.project_root / self.logging.dir
        self._report_dir_path = self.project_root / self.report.output_dir

    @property
    def cache_dir_path(self) -> Path:
        return self._cache_dir_path

    @property
    def log_dir_path(self) -> Path:
        return self._log_dir_path

    @property
    def report_dir_path(self) -> Path:
        return self._report_dir_path

    def ensure_dirs(self):
        """确保所有必要的目录存在。"""
        for dir_path in [self.cache_dir_path, self.log_dir_path, self.report_dir_path]:
            dir_path.mkdir(parents=True, exist_ok=True)


# 全局配置单例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置单例。

    Returns:
        Settings: 全局配置实例。
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings():
    """重置全局配置单例（主要用于测试）。"""
    global _settings
    _settings = None
