# Tasks

- [x] Task 1: 统一配置管理系统
  - [x] SubTask 1.1: 创建 `config/` 目录，编写 `config/default.yaml` 默认配置文件，包含所有配置项分类（server、database、redis、celery、datasource、analysis、report、logging）及注释说明
  - [x] SubTask 1.2: 编写 `config/development.yaml` 开发环境配置和 `config/production.yaml` 生产环境配置
  - [x] SubTask 1.3: 创建 `config/settings.py`，基于 Pydantic BaseSettings 实现统一配置加载类 `Settings`，支持 YAML 文件加载、环境变量覆盖、.env 敏感信息读取、配置验证
  - [x] SubTask 1.4: 创建 `config/__init__.py`，提供 `get_settings()` 全局单例访问函数
  - [x] SubTask 1.5: 更新 `.env.example`，新增数据库、Redis、Celery、API服务相关敏感配置项模板
  - [x] SubTask 1.6: 为统一配置管理系统编写单元测试，验证 YAML 加载、环境变量覆盖、配置验证、多环境切换

- [x] Task 2: 项目目录结构规范化重构
  - [x] SubTask 2.1: 创建 `etf_analyzer/core/` 包，将 `analyzer.py`、`data_fetcher.py`、`data_processor.py`、`visualizer.py`、`report_generator.py` 迁移至此，更新内部导入
  - [x] SubTask 2.2: 创建 `etf_analyzer/services/` 包，将 `data_source_manager.py`、`data_completion.py`、`incremental_updater.py`、`data_monitor.py` 迁移至此，更新内部导入
  - [x] SubTask 2.3: 创建 `etf_analyzer/utils/` 包，将 `logger.py`、`retry.py`、`secure_config.py` 迁移至此，更新内部导入
  - [x] SubTask 2.4: 更新 `etf_analyzer/__init__.py`，重新导出核心类和函数，确保旧式导入路径向后兼容
  - [x] SubTask 2.5: 更新 `main.py` CLI入口，适配新的目录结构和配置系统
  - [x] SubTask 2.6: 更新 `tests/` 下所有测试文件的导入路径
  - [x] SubTask 2.7: 删除 `etf_analyzer/config.py` 旧配置文件（功能已迁移至 `config/settings.py`），更新所有引用

- [x] Task 3: 数据库持久化层
  - [x] SubTask 3.1: 创建 `db/` 包，编写 `db/database.py`，实现 SQLAlchemy 异步引擎和会话管理，支持连接池配置
  - [x] SubTask 3.2: 编写 `db/models.py`，定义 ETF 基础信息表（ETFInfo）和历史数据缓存表（HistoryDataCache）SQLAlchemy 模型
  - [x] SubTask 3.3: 编写 `db/crud.py`，实现 ETF 信息和历史数据的 CRUD 操作（查询、插入、更新、批量写入）
  - [x] SubTask 3.4: 实现数据库自动建表逻辑，首次启动时自动创建所需表结构
  - [x] SubTask 3.5: 为数据库层编写单元测试（使用 SQLite 内存数据库进行测试）

- [x] Task 4: FastAPI 后端API服务
  - [x] SubTask 4.1: 创建 `api/` 包结构（`api/routers/`、`api/schemas/`、`api/services/`）
  - [x] SubTask 4.2: 编写 `api/main.py`，创建 FastAPI 应用实例，配置 CORS、路由挂载、生命周期事件（启动时初始化数据库连接）
  - [x] SubTask 4.3: 编写 `api/schemas/etf.py`，定义 ETF 相关 Pydantic 请求/响应模型
  - [x] SubTask 4.4: 编写 `api/schemas/analysis.py`，定义分析相关 Pydantic 请求/响应模型
  - [x] SubTask 4.5: 编写 `api/schemas/report.py`，定义报告相关 Pydantic 请求/响应模型
  - [x] SubTask 4.6: 编写 `api/routers/etf.py`，实现 ETF 数据查询 API（列表、实时行情、历史数据、持仓信息）
  - [x] SubTask 4.7: 编写 `api/routers/analysis.py`，实现分析计算 API（净值走势、风险指标、绩效分析、成分股、行业分布）
  - [x] SubTask 4.8: 编写 `api/routers/chart.py`，实现图表生成 API（K线图、净值走势图、行业分布图、成分股图、回撤曲线图）
  - [x] SubTask 4.9: 编写 `api/routers/report.py`，实现报告生成 API（异步生成、任务状态查询、报告下载）
  - [x] SubTask 4.10: 编写 `api/deps.py`，实现依赖注入（数据库会话、配置、核心服务实例）
  - [x] SubTask 4.11: 为 API 路由编写单元测试（使用 FastAPI TestClient）

- [x] Task 5: Celery 异步任务处理
  - [x] SubTask 5.1: 创建 `tasks/` 包，编写 `tasks/celery_app.py`，配置 Celery 应用（broker、backend、序列化等）
  - [x] SubTask 5.2: 编写 `tasks/report_tasks.py`，实现异步报告生成任务
  - [x] SubTask 5.3: 编写 `tasks/batch_tasks.py`，实现批量分析任务
  - [x] SubTask 5.4: 为 Celery 任务编写单元测试

- [x] Task 6: Vue 3 前端可视化界面
  - [x] SubTask 6.1: 初始化 Vue 3 + Vite 项目到 `frontend/` 目录，配置 TypeScript、Element Plus UI 组件库、ECharts 图表库
  - [x] SubTask 6.2: 实现前端布局框架（顶部导航栏、侧边菜单、主内容区）
  - [x] SubTask 6.3: 实现 ETF 搜索与列表展示页面，支持关键词搜索和分页
  - [x] SubTask 6.4: 实现实时行情看板页面，展示ETF关键行情指标
  - [x] SubTask 6.5: 实现交互式图表页面（K线图、净值走势图、行业分布图等），基于 ECharts 支持缩放和拖拽
  - [x] SubTask 6.6: 实现分析报告在线预览页面，支持PDF下载
  - [x] SubTask 6.7: 封装后端 API 调用层（axios），统一错误处理和请求拦截

- [x] Task 7: 依赖更新与集成验证
  - [x] SubTask 7.1: 更新 `requirements.txt`，新增 fastapi、uvicorn、sqlalchemy、pymysql、celery、redis、pydantic-settings、pyyaml 等依赖
  - [x] SubTask 7.2: 编写启动脚本 `run.py`，支持一键启动 API 服务、Celery Worker
  - [x] SubTask 7.3: 端到端集成测试，验证 API 接口、数据库读写、异步任务、前端页面联动

- [x] Task 8: 修复验证未通过的检查点
  - [x] SubTask 8.1: 修复检查点3 - Settings 类添加 env_file=".env" 配置，支持 .env 文件自动读取
  - [x] SubTask 8.2: 修复检查点14 - 迁移所有 etf_analyzer.config 引用至 config/settings.py，删除旧 etf_analyzer/config.py
  - [x] SubTask 8.3: 修复检查点12 - main.py 适配新配置系统，从 config.settings 获取配置
  - [x] SubTask 8.4: 修复检查点13 - 更新 test_full_validation.py 中的旧式导入路径
  - [x] SubTask 8.5: 修复检查点25 - 报告生成 API 改为异步任务，返回 task_id
  - [x] SubTask 8.6: 修复检查点26 - 任务状态查询 API 接入 Celery 实际状态查询
  - [x] SubTask 8.7: 修复检查点36 - ChartsView 使用 ECharts 实现交互式图表（缩放、拖拽）
  - [x] SubTask 8.8: 修复检查点37 - ReportView 添加异步任务轮询、PDF预览和下载功能
  - [x] SubTask 8.9: 修复检查点40 - 编写端到端集成测试

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 1, Task 2, Task 3]
- [Task 5] depends on [Task 1, Task 3]
- [Task 6] depends on [Task 4]
- [Task 7] depends on [Task 1, Task 2, Task 3, Task 4, Task 5, Task 6]
- [Task 8] depends on [Task 1, Task 2, Task 3, Task 4, Task 5, Task 6]
