# Web可视化界面与RESTful API服务 Spec

## Why
当前ETF分析工具仅支持命令行界面，交互方式单一，无法支持远程访问和多用户并发。需要将现有命令行工具升级为Web服务，提供可视化界面和API接口，同时设计统一的配置文件管理系统，并对项目目录结构进行规范化重构，使其符合行业最佳实践。

## What Changes
- 新增统一配置管理系统（基于 Pydantic BaseSettings + YAML 配置文件），整合所有可配置项
- 重构项目目录结构，按职责分层组织代码（核心层、API层、数据层、任务层、前端层）
- 新增后端API服务（基于 FastAPI），提供ETF数据查询、分析计算、图表生成、报告生成等RESTful接口
- 新增前端可视化界面（基于 Vue 3），提供ETF搜索、行情看板、交互式图表、报告预览
- 新增数据持久化层（基于 SQLAlchemy + MySQL），建立ETF基础信息表和历史数据缓存表
- 新增异步任务处理（基于 Celery + Redis），支持异步报告生成和批量分析任务队列
- 修改现有 `config.py` 和 `secure_config.py`，迁移至统一配置管理系统
- 修改现有模块导入路径，适配新的目录结构
- **BREAKING**: 模块导入路径变更，外部代码需更新导入语句

## Impact
- Affected specs: build-etf-analyzer（配置模块、目录结构变更）、multi-datasource-expansion（配置模块、目录结构变更）
- Affected code: `etf_analyzer/` 下所有模块（目录重组）、`main.py`（入口适配）、`config.py`（迁移至新配置系统）、`secure_config.py`（整合至新配置系统）、`requirements.txt`（新增依赖）

## ADDED Requirements

### Requirement: 统一配置管理系统
系统 SHALL 提供基于 YAML 配置文件和 Pydantic BaseSettings 的统一配置管理，将所有可配置项集中管理。

#### Scenario: 从 YAML 配置文件加载非敏感配置
- **WHEN** 系统启动并初始化配置
- **THEN** 从 `config/default.yaml` 加载默认配置，根据 `ETF_ENV` 环境变量加载对应环境配置文件（如 `config/development.yaml`、`config/production.yaml`），环境配置覆盖默认配置

#### Scenario: 从环境变量覆盖配置
- **WHEN** 系统环境变量中存在与配置项同名的变量
- **THEN** 环境变量值覆盖 YAML 配置文件中的值，优先级：环境变量 > 环境YAML > 默认YAML

#### Scenario: 敏感信息管理
- **WHEN** 配置项涉及敏感信息（数据库密码、API Token、Redis密码等）
- **THEN** 敏感信息通过 `.env` 文件或环境变量提供，不写入 YAML 配置文件，YAML 中仅包含占位符或空值

#### Scenario: 配置验证与类型检查
- **WHEN** 配置加载完成
- **THEN** Pydantic BaseSettings 自动验证配置项的类型和值，类型不匹配或必需项缺失时抛出明确的验证错误

#### Scenario: 配置项分类组织
- **WHEN** 用户查看或修改配置
- **THEN** 配置项按功能模块分类组织，包括：server（API服务）、database（数据库）、redis（缓存）、celery（异步任务）、datasource（数据源）、analysis（分析参数）、report（报告）、logging（日志）

#### Scenario: 配置文件模板
- **WHEN** 新用户首次部署项目
- **THEN** 项目提供 `config/default.yaml` 作为完整配置模板，包含所有可配置项及注释说明，用户只需复制并修改即可

### Requirement: 项目目录结构规范化
系统 SHALL 按职责分层重构项目目录结构，符合 Python Web 项目行业最佳实践。

#### Scenario: 核心业务逻辑层
- **WHEN** 项目目录重构完成
- **THEN** 核心分析逻辑（analyzer、data_fetcher、data_processor、visualizer、report_generator）位于 `etf_analyzer/core/` 包下

#### Scenario: 数据源层
- **WHEN** 项目目录重构完成
- **THEN** 数据源相关代码（base、akshare_source、tushare_source、baostock_source、pytdx_source）位于 `etf_analyzer/data_sources/` 包下（保持现有位置不变）

#### Scenario: 服务层
- **WHEN** 项目目录重构完成
- **THEN** 服务层代码（data_source_manager、data_completion、incremental_updater、data_monitor）位于 `etf_analyzer/services/` 包下

#### Scenario: 工具层
- **WHEN** 项目目录重构完成
- **THEN** 工具类代码（logger、retry、secure_config）位于 `etf_analyzer/utils/` 包下

#### Scenario: API层
- **WHEN** 项目目录重构完成
- **THEN** FastAPI 应用代码位于 `api/` 包下，包含路由（routers/）、数据模型（schemas/）、API服务（services/）

#### Scenario: 数据库层
- **WHEN** 项目目录重构完成
- **THEN** 数据库相关代码（模型定义、连接管理、CRUD操作）位于 `db/` 包下

#### Scenario: 异步任务层
- **WHEN** 项目目录重构完成
- **THEN** Celery 异步任务代码位于 `tasks/` 包下

#### Scenario: 配置文件目录
- **WHEN** 项目目录重构完成
- **THEN** 配置文件（YAML、.env 模板）位于 `config/` 目录下

#### Scenario: 向后兼容
- **WHEN** 目录结构重构后
- **THEN** `etf_analyzer/__init__.py` 中重新导出核心类和函数，使旧式导入路径（如 `from etf_analyzer.analyzer import ETFAnalyzer`）仍然可用

### Requirement: 后端API服务
系统 SHALL 基于 FastAPI 提供 RESTful API 接口，支持 ETF 数据查询、分析计算、图表生成和报告生成。

#### Scenario: ETF数据查询API
- **WHEN** 客户端发送 GET /api/v1/etf/list 请求
- **THEN** 返回ETF列表数据，支持关键词搜索和分页

#### Scenario: ETF实时行情API
- **WHEN** 客户端发送 GET /api/v1/etf/{symbol}/quote 请求
- **THEN** 返回指定ETF的实时行情数据

#### Scenario: ETF历史数据API
- **WHEN** 客户端发送 GET /api/v1/etf/{symbol}/history 请求（含日期范围参数）
- **THEN** 返回指定ETF的历史K线数据

#### Scenario: ETF持仓信息API
- **WHEN** 客户端发送 GET /api/v1/etf/{symbol}/holdings 请求
- **THEN** 返回指定ETF的持仓信息

#### Scenario: 净值走势分析API
- **WHEN** 客户端发送 POST /api/v1/analysis/nav-trend 请求（含ETF代码和日期范围）
- **THEN** 返回净值走势分析结果

#### Scenario: 风险指标计算API
- **WHEN** 客户端发送 POST /api/v1/analysis/risk-metrics 请求
- **THEN** 返回风险指标计算结果

#### Scenario: 绩效分析API
- **WHEN** 客户端发送 POST /api/v1/analysis/performance 请求
- **THEN** 返回绩效分析结果

#### Scenario: 图表生成API
- **WHEN** 客户端发送 POST /api/v1/chart/{chart_type} 请求
- **THEN** 生成指定类型的图表并返回图片URL

#### Scenario: 报告生成API（异步）
- **WHEN** 客户端发送 POST /api/v1/report/generate 请求
- **THEN** 创建异步报告生成任务，返回任务ID

#### Scenario: 报告任务状态查询API
- **WHEN** 客户端发送 GET /api/v1/report/task/{task_id} 请求
- **THEN** 返回报告生成任务的状态和进度

#### Scenario: API文档自动生成
- **WHEN** 访问 /docs 路径
- **THEN** 自动生成并展示 Swagger UI 格式的 API 文档

### Requirement: 数据持久化
系统 SHALL 基于 SQLAlchemy + MySQL 实现数据持久化，缓存ETF基础信息和历史数据。

#### Scenario: ETF基础信息持久化
- **WHEN** 系统首次获取ETF列表数据
- **THEN** 将ETF基础信息（代码、名称、类型、规模等）写入数据库，后续查询优先从数据库读取

#### Scenario: 历史数据缓存
- **WHEN** 系统获取ETF历史数据
- **THEN** 将历史数据写入数据库缓存表，后续相同查询直接从数据库读取

#### Scenario: 数据库连接配置
- **WHEN** 用户在配置文件中设置数据库连接参数（host、port、database、user、password）
- **THEN** 系统使用配置的参数建立数据库连接

#### Scenario: 数据库连接池
- **WHEN** 系统处理并发请求
- **THEN** 使用数据库连接池管理连接，避免频繁创建和销毁连接

#### Scenario: 数据库自动建表
- **WHEN** 系统首次启动且数据库中不存在所需表
- **THEN** 自动创建ETF基础信息表、历史数据缓存表等必要表结构

### Requirement: 异步任务处理
系统 SHALL 基于 Celery + Redis 实现异步任务处理，支持报告生成和批量分析。

#### Scenario: 异步报告生成
- **WHEN** 用户通过API请求生成报告
- **THEN** 系统创建Celery异步任务，立即返回任务ID，报告在后台生成

#### Scenario: 批量分析任务
- **WHEN** 用户提交多个ETF的批量分析请求
- **THEN** 系统将批量任务加入Celery队列，按顺序或并行执行

#### Scenario: 任务状态查询
- **WHEN** 用户查询异步任务状态
- **THEN** 返回任务状态（PENDING、STARTED、SUCCESS、FAILURE）和进度信息

#### Scenario: Celery配置
- **WHEN** 用户在配置文件中设置Celery相关参数（broker_url、result_backend等）
- **THEN** 系统使用配置的参数初始化Celery应用

### Requirement: 前端可视化界面
系统 SHALL 基于 Vue 3 提供可视化Web界面。

#### Scenario: ETF搜索与列表展示
- **WHEN** 用户在搜索框输入关键词
- **THEN** 实时搜索并展示匹配的ETF列表，显示代码、名称、最新价、涨跌幅等

#### Scenario: 实时行情看板
- **WHEN** 用户选择某只ETF
- **THEN** 展示该ETF的实时行情看板，包含最新价、涨跌幅、成交量等关键指标

#### Scenario: 交互式图表
- **WHEN** 用户选择图表类型和时间范围
- **THEN** 展示可缩放、可拖拽的交互式图表（K线图、净值走势图、行业分布图等）

#### Scenario: 分析报告在线预览
- **WHEN** 用户请求生成分析报告
- **THEN** 在浏览器中在线预览报告内容，支持下载PDF

### Requirement: API服务配置
系统 SHALL 支持API服务的运行参数配置。

#### Scenario: 服务端口配置
- **WHEN** 用户在配置文件中设置服务端口（默认8000）
- **THEN** API服务在指定端口启动

#### Scenario: 跨域配置
- **WHEN** 用户配置允许的跨域来源
- **THEN** API服务按配置设置CORS策略

#### Scenario: API前缀配置
- **WHEN** 用户配置API路由前缀（默认 /api/v1）
- **THEN** 所有API接口使用配置的前缀

## MODIFIED Requirements

### Requirement: 配置模块
系统 SHALL 通过统一配置管理系统（Pydantic BaseSettings + YAML）管理所有配置项，替代原有的 `config.py` 硬编码常量和 `secure_config.py` 分散管理方式。

#### Scenario: 配置加载
- **WHEN** 系统启动并初始化配置
- **THEN** 从 YAML 配置文件加载非敏感配置，从 .env 文件和环境变量加载敏感配置，合并后提供统一访问接口

#### Scenario: 配置访问
- **WHEN** 模块需要访问配置项
- **THEN** 通过 `get_settings()` 函数获取全局配置单例，按属性访问各配置项

#### Scenario: 旧配置兼容
- **WHEN** 现有代码使用 `from etf_analyzer.config import XXX` 方式访问配置
- **THEN** 旧导入路径仍然可用，内部从新配置系统获取值

### Requirement: 数据获取模块
系统 SHALL 在数据获取时优先从数据库缓存读取，缓存未命中时通过数据源管理器获取并写入缓存。

#### Scenario: 数据库缓存优先
- **WHEN** 用户请求ETF数据
- **THEN** 系统先查询数据库缓存，缓存命中且未过期则直接返回，否则从数据源获取并更新缓存

## REMOVED Requirements

### Requirement: 硬编码配置常量
**Reason**: 迁移至统一配置管理系统，所有配置项从 YAML 文件和环境变量加载
**Migration**: `config.py` 中的硬编码常量迁移至 `config/default.yaml`，通过 Pydantic BaseSettings 访问
