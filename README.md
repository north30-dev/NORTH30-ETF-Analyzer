# NORTH30-ETF-Analyzer

全链路 ETF 分析平台，支持命令行（CLI）和 Web 可视化界面（Vue 3 + RESTful API）两种使用方式。提供多数据源获取、智能数据补全、增量更新与异常预警，量化策略分析与回测框架，以及从数据获取、清洗、分析、策略回测到可视化与报告生成的全链路能力。

## 功能特性

### 多数据源获取
- **实时行情** — 获取任意 ETF 的最新价格、涨跌幅、成交量等关键指标
- **历史数据** — 支持自定义时间范围的历史K线数据获取，支持前复权/后复权/不复权
- **ETF列表** — 获取全市场 ETF 列表，支持按关键词搜索
- **持仓信息** — 查询 ETF 成分股构成及持仓占比
- **多数据源支持** — 支持 Akshare、Tushare、Baostock、通达信(pytdx) 四种数据源，按优先级自动切换与故障转移
- **安全配置管理** — Token/API Key 通过 `.env` 文件管理，支持 dev/prod 多环境配置

### 智能数据补全
- **缺失日期填充** — 自动检测并填充交易日历中的缺失日期，支持 interpolate/neighbor_mean 等方法
- **缺失值填充** — 对数据中的空值进行插值或均值填充，标记补全行
- **多源交叉验证** — 对比不同数据源的同一指标，自动检测差异并标记冲突
- **数据质量评分** — 综合完整性、来源数、一致性计算 0-100 质量评分

### 增量更新
- **版本管理** — 基于本地 JSON 文件记录每次更新的版本、记录数、来源和时间戳
- **增量同步** — 仅获取上次更新之后的新数据，避免重复拉取
- **定时更新** — 支持配置定时更新计划，指定 ETF 列表、更新时间和星期

### 数据异常预警
- **健康检查** — 定期检测各数据源可用性与响应时间
- **连续失败告警** — 数据源连续失败次数超过阈值时触发告警
- **质量报告** — 生成包含各数据源状态、可用率、响应时间的结构化报告

### 数据处理
- **数据清洗** — 缺失值填充、异常值检测与修正、数据类型统一转换
- **标准化/归一化** — Min-Max 归一化与 Z-Score 标准化
- **数据验证** — 完整性、类型正确性、数值合理性多维度验证

### 核心分析
- **净值走势分析** — 累计/年化收益率计算、基于均线的趋势判断（MA20/MA60）
- **成分股构成分析** — 前十大权重股提取、持仓集中度计算
- **行业分布统计** — 支持申万一级与中信一级行业分类标准
- **风险指标计算** — 日/年化波动率、最大回撤（含起止日期）、夏普比率、信息比率
- **绩效分析** — 超额收益、跟踪误差、信息比率、胜率

### 可视化
- **K线图** — 含成交量副图的蜡烛图
- **净值走势图** — 支持叠加基准指数对比曲线
- **行业分布饼图** — 自动合并占比小于 3% 的行业
- **成分股权重柱状图** — 前十大权重股水平柱状图，标注占比
- **回撤曲线图** — 展示回撤演变过程

### 报告生成
- **PDF 报告** — 自动生成包含封面、目录、指标概览、图表和文字分析的 PDF
- **自定义模块** — 按需选择报告包含的分析模块

### Web 可视化界面（新增）
- **RESTful API 服务** — 基于 FastAPI 提供 ETF 数据查询、分析计算、图表生成、报告生成等 RESTful 接口
- **交互式图表** — 基于 ECharts 实现 K 线图、净值走势图等交互式图表，支持缩放与拖拽
- **异步任务** — 基于 Celery + Redis 实现报告异步生成，支持任务进度查询
- **数据库持久化** — 基于 SQLAlchemy + MySQL 实现 ETF 信息与历史数据持久化存储

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 数据源 | [akshare](https://github.com/akfamily/akshare)、[tushare](https://tushare.pro/)、[baostock](http://baostock.com/)、[pytdx](https://github.com/rainx/pytdx) |
| 配置管理 | [Pydantic BaseSettings](https://docs.pydantic.dev/latest/) + YAML（多环境配置） |
| 数据处理 | [pandas](https://pandas.pydata.org/)、[numpy](https://numpy.org/) |
| 可视化（CLI） | [matplotlib](https://matplotlib.org/)、[mplfinance](https://github.com/matplotlib/mplfinance) |
| 报告生成 | [reportlab](https://www.reportlab.com/)（PDF 生成） |
| RESTful API | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| 数据库 ORM | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [PyMySQL](https://pypi.org/project/PyMySQL/) |
| 异步任务 | [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) |
| 前端框架 | [Vue 3](https://vuejs.org/) + [Vite](https://vitejs.dev/) |
| UI 组件库 | [Element Plus](https://element-plus.org/) |
| 交互式图表 | [ECharts](https://echarts.apache.org/) + [vue-echarts](https://github.com/ecomfe/vue-echarts) |
| 测试框架 | [pytest](https://pytest.org/)、[pytest-cov](https://pytest-cov.readthedocs.io/) |

## 架构设计

```
主入口层
  main.py              命令行交互入口（ETFCLI 类）
  run.py               启动脚本（支持 api / celery 子命令）
      │
核心模块层 (etf_analyzer/)
  ├── core/             核心分析模块
  │   ├── analyzer.py          ETFAnalyzer（净值走势/风险指标/绩效分析）
  │   ├── data_fetcher.py      ETFDataFetcher（数据获取调度）
  │   ├── data_processor.py    DataProcessor（数据清洗/验证）
  │   ├── visualizer.py        ETFVisualizer（图表生成）
  │   └── report_generator.py  ReportGenerator（PDF报告生成）
  ├── services/          服务层
  │   ├── data_source_manager.py   数据源管理器（注册/优先级/故障转移）
  │   ├── data_completion.py       智能数据补全（缺失填充/交叉验证/质量评分）
  │   ├── incremental_updater.py   增量更新（版本管理/定时更新）
  │   └── data_monitor.py          数据异常预警（健康检查/告警/质量报告）
  ├── utils/             工具层
  │   ├── logger.py          日志模块
  │   ├── retry.py           重试装饰器
  │   └── secure_config.py   安全配置管理（.env 多环境）
  ├── data_sources/      数据源抽象层
  │   ├── base.py              抽象基类 BaseDataSource
  │   ├── akshare_source.py    Akshare 数据源
  │   ├── tushare_source.py    Tushare 数据源
  │   ├── baostock_source.py   Baostock 数据源
  │   └── pytdx_source.py      通达信数据源
  └── __init__.py         延迟导入，旧式导入路径向后兼容

配置层 (config/)
  ├── __init__.py         统一配置入口（get_settings() 单例）
  ├── settings.py         Pydantic BaseSettings 配置类
  ├── default.yaml        默认配置文件（9大分类）
  ├── development.yaml    开发环境覆盖配置
  └── production.yaml     生产环境覆盖配置

API 服务层 (api/)
  ├── main.py             FastAPI 应用入口（CORS/路由/生命周期）
  ├── deps.py             依赖注入（单例组件）
  ├── routers/            API 路由
  │   ├── etf.py          ETF 数据查询（列表/行情/历史/持仓）
  │   ├── analysis.py     分析计算（净值/风险/绩效/行业分布）
  │   ├── chart.py        图表生成（K线/净值/饼图/柱状图/回撤）
  │   └── report.py       报告生成（Celery 异步任务）
  └── schemas/            Pydantic 请求/响应模型
      ├── etf.py
      ├── analysis.py
      └── report.py

数据库层 (db/)
  ├── database.py         SQLAlchemy 引擎与会话管理
  ├── models.py           ORM 模型（ETFInfo / HistoryDataCache）
  └── crud.py             CRUD 操作

异步任务层 (tasks/)
  ├── celery_app.py       Celery 应用配置
  ├── report_tasks.py     异步报告生成任务（5步进度更新）
  └── batch_tasks.py      批量分析任务

前端层 (frontend/)
  └── src/
      ├── main.js         Vue 3 应用入口
      ├── App.vue         布局框架
      ├── router/         路由配置
      ├── api/            Axios API 封装
      └── views/          页面组件
          ├── HomeView.vue      首页/概览
          ├── ETFView.vue       ETF 搜索与列表
          ├── AnalysisView.vue  净值走势与风险分析
          ├── ChartsView.vue    交互式图表（ECharts）
          └── ReportView.vue    报告生成与预览（PDF）
```

各模块间通过类方法调用形成单向依赖链：
`数据获取 → 数据处理 → 核心分析 → 可视化 → 报告生成`

数据获取层内部架构：
`ETFDataFetcher → DataSourceManager → BaseDataSource 子类（按优先级自动故障转移）`

## 环境要求

- Python 3.9+
- Node.js 18+（前端开发）
- MySQL 8.0+（可选，数据库持久化）
- Redis 6.0+（可选，Celery 异步任务）
- Windows / macOS / Linux
- 网络连接（用于获取金融数据）

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/north30-dev/NORTH30-ETF-Analyzer.git
cd NORTH30-ETF-Analyzer
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，填入必要的配置（如 Tushare Token、数据库连接等）
```

`.env` 配置项说明：

| 配置项 | 必填 | 说明 |
|--------|------|------|
| `ETF_ENV` | 否 | 运行环境：dev / prod，默认 dev |
| `TUSHARE_TOKEN` | 否 | Tushare 数据源 Token，不配置则跳过该数据源 |
| `PYTDX_HOST` | 否 | 通达信服务器地址，默认 `119.147.212.81` |
| `PYTDX_PORT` | 否 | 通达信服务器端口，默认 `7709` |
| `DB_HOST` | 否 | 数据库主机，默认 `localhost` |
| `DB_PORT` | 否 | 数据库端口，默认 `3306` |
| `DB_USER` | 否 | 数据库用户名 |
| `DB_PASSWORD` | 否 | 数据库密码 |
| `REDIS_HOST` | 否 | Redis 主机，默认 `127.0.0.1` |
| `REDIS_PORT` | 否 | Redis 端口，默认 `6379` |
| `REDIS_PASSWORD` | 否 | Redis 密码 |

> Akshare 和 Baostock 无需 Token 即可使用；Tushare 需要在 `.env` 中配置 Token。

### 5. 安装前端依赖（可选，Web 界面）

```bash
cd frontend
npm install
cd ..
```

## 使用指南

### 命令行模式 (CLI)

```bash
python main.py
```

程序启动后显示主菜单：

```
========================================
    ETF 分析工具 v2.0
========================================
1. 数据获取
2. 数据分析
3. 数据可视化
4. 报告生成
0. 退出
========================================
请选择操作（输入数字）:
```

### Web 服务模式

#### 启动 API 服务

```bash
# 方式一：使用启动脚本
python run.py api

# 方式二：直接使用 uvicorn
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档地址：`http://localhost:8000/docs`（Swagger UI）

#### 启动 Celery Worker（异步任务）

```bash
python run.py celery
```

#### 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端地址：`http://localhost:5173`

#### API 路由概览

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/v1/etf/list` | GET | ETF 列表查询 |
| `/api/v1/etf/{symbol}/quote` | GET | 实时行情 |
| `/api/v1/etf/{symbol}/history` | GET | 历史数据 |
| `/api/v1/etf/{symbol}/holdings` | GET | 持仓信息 |
| `/api/v1/analysis/nav-trend` | POST | 净值走势分析 |
| `/api/v1/analysis/risk-metrics` | POST | 风险指标计算 |
| `/api/v1/analysis/performance` | POST | 绩效分析 |
| `/api/v1/analysis/holdings` | POST | 成分股分析 |
| `/api/v1/analysis/industry-distribution` | POST | 行业分布统计 |
| `/api/v1/chart/generate` | POST | 图表生成 |
| `/api/v1/report/generate` | POST | 报告生成（异步） |
| `/api/v1/report/task/{task_id}` | GET | 任务状态查询 |

### 常见操作示例

```bash
# 启动 CLI 程序
python main.py

# 启动 API 服务
python run.py api

# 查看 API 文档
# 浏览器打开 http://localhost:8000/docs

# 生成 ETF 分析报告
python main.py  # 菜单中选择 4 → 1 → 输入 ETF 代码（如 510300）
```

### 运行测试

```bash
# 运行全部测试（含单元测试 + 集成测试）
pytest tests/ -v

# 运行带覆盖率的测试
pytest tests/ -v --cov=etf_analyzer --cov-report=term-missing

# 运行指定测试模块
pytest tests/test_api.py -v
pytest tests/test_database.py -v
pytest tests/test_integration.py -v

# 运行综合功能验证
python tests/test_full_validation.py
```

## 项目目录

```
NORTH30-ETF-Analyzer/
├── main.py                          # 命令行交互入口
├── run.py                           # 启动脚本（api / celery 子命令）
├── requirements.txt                 # Python 依赖清单
├── .env.example                     # 环境配置模板
├── .gitignore
├── config/                          # 统一配置管理
│   ├── __init__.py                  # 配置入口（get_settings 单例）
│   ├── settings.py                  # Pydantic BaseSettings 配置类
│   ├── default.yaml                 # 默认配置（9大分类）
│   ├── development.yaml             # 开发环境覆盖
│   └── production.yaml              # 生产环境覆盖
├── etf_analyzer/                    # 核心模块包
│   ├── __init__.py                  # 延迟导入，向后兼容
│   ├── core/                        # 核心分析模块
│   │   ├── __init__.py
│   │   ├── analyzer.py              # 核心分析（净值/风险/绩效）
│   │   ├── data_fetcher.py          # 数据获取调度
│   │   ├── data_processor.py        # 数据处理（清洗/验证）
│   │   ├── visualizer.py            # 图表生成
│   │   └── report_generator.py      # PDF 报告生成
│   ├── services/                    # 服务层
│   │   ├── __init__.py
│   │   ├── data_source_manager.py   # 数据源管理器
│   │   ├── data_completion.py       # 智能数据补全
│   │   ├── incremental_updater.py   # 增量更新
│   │   └── data_monitor.py          # 数据异常预警
│   ├── utils/                       # 工具层
│   │   ├── __init__.py
│   │   ├── logger.py                # 日志模块
│   │   ├── retry.py                 # 重试装饰器
│   │   └── secure_config.py         # 安全配置管理
│   ├── data_sources/                # 数据源抽象层
│   │   ├── __init__.py
│   │   ├── base.py                  # 抽象基类
│   │   ├── akshare_source.py        # Akshare 数据源
│   │   ├── tushare_source.py        # Tushare 数据源
│   │   ├── baostock_source.py       # Baostock 数据源
│   │   └── pytdx_source.py          # 通达信数据源
│   ├── analyzer.py                  # [兼容层] → core.analyzer
│   ├── data_fetcher.py              # [兼容层] → core.data_fetcher
│   ├── data_processor.py            # [兼容层] → core.data_processor
│   ├── visualizer.py                # [兼容层] → core.visualizer
│   ├── report_generator.py          # [兼容层] → core.report_generator
│   ├── data_source_manager.py       # [兼容层] → services.data_source_manager
│   ├── data_completion.py           # [兼容层] → services.data_completion
│   ├── incremental_updater.py       # [兼容层] → services.incremental_updater
│   ├── data_monitor.py              # [兼容层] → services.data_monitor
│   ├── secure_config.py             # [兼容层] → utils.secure_config
│   ├── logger.py                    # [兼容层] → utils.logger
│   └── retry.py                     # [兼容层] → utils.retry
├── api/                             # RESTful API 服务
│   ├── main.py                      # FastAPI 应用入口
│   ├── deps.py                      # 依赖注入
│   ├── routers/
│   │   ├── etf.py                   # ETF 数据查询
│   │   ├── analysis.py              # 分析计算
│   │   ├── chart.py                 # 图表生成
│   │   └── report.py                # 报告生成（异步）
│   └── schemas/
│       ├── etf.py                   # ETF 请求/响应模型
│       ├── analysis.py              # 分析请求/响应模型
│       └── report.py                # 报告请求/响应模型
├── db/                              # 数据库持久化层
│   ├── database.py                  # SQLAlchemy 引擎与会话管理
│   ├── models.py                    # ORM 模型
│   └── crud.py                      # CRUD 操作
├── tasks/                           # Celery 异步任务
│   ├── celery_app.py                # Celery 应用配置
│   ├── report_tasks.py              # 异步报告生成
│   └── batch_tasks.py               # 批量分析
├── frontend/                        # Vue 3 前端（Web 界面）
│   ├── package.json
│   ├── vite.config.js               # Vite 配置（含 API 代理）
│   ├── index.html
│   └── src/
│       ├── main.js                  # 应用入口
│       ├── App.vue                  # 布局框架
│       ├── router/index.js          # 路由配置
│       ├── api/index.js             # Axios API 封装
│       └── views/
│           ├── HomeView.vue         # 首页概览
│           ├── ETFView.vue          # ETF 搜索与列表
│           ├── AnalysisView.vue     # 分析看板
│           ├── ChartsView.vue       # 交互式图表
│           └── ReportView.vue       # 报告生成与预览
├── tests/                           # 测试
│   ├── __init__.py
│   ├── conftest.py                  # 测试 fixtures
│   ├── test_settings.py             # 配置系统测试
│   ├── test_secure_config.py        # 安全配置测试
│   ├── test_data_sources.py         # 数据源测试
│   ├── test_data_source_manager.py  # 数据源管理器测试
│   ├── test_data_completion.py      # 数据补全测试
│   ├── test_data_fetcher.py         # 数据获取测试
│   ├── test_data_processor.py       # 数据处理测试
│   ├── test_analyzer.py             # 核心分析测试
│   ├── test_database.py             # 数据库层测试
│   ├── test_api.py                  # API 路由测试
│   ├── test_celery_tasks.py         # Celery 任务测试
│   ├── test_integration.py          # 端到端集成测试
│   └── test_full_validation.py      # 综合功能验证
├── cache/                           # 数据缓存（运行时创建）
├── logs/                            # 日志文件（运行时创建）
├── reports/                         # 报告输出（运行时创建）
└── charts/                          # 图表输出（运行时创建）
```

## 配置文件说明

### 统一配置系统（config/）

项目采用基于 Pydantic BaseSettings + YAML 的分层配置架构：

**配置优先级（从高到低）**：
1. 环境变量（如 `DB_HOST=localhost`）
2. `.env` 文件（敏感信息，不纳入版本管理）
3. `config/production.yaml` 或 `config/development.yaml`（环境特定配置）
4. `config/default.yaml`（默认配置，所有环境共享）

**配置分类（default.yaml）**：

| 分类 | 说明 |
|------|------|
| server | API 服务配置（host、port、cors_origins、debug） |
| database | 数据库连接（host、port、name、user、password、pool_size） |
| redis | Redis 连接（host、port、db、password） |
| celery | Celery 异步任务（broker_url、result_backend、worker_concurrency） |
| datasource | 数据源配置（priority、health_check_interval、failure_threshold） |
| analysis | 分析参数（default_start_date、risk_free_rate） |
| strategy | 策略参数（momentum、mean_reversion、sector_rotation、multi_factor） |
| backtest | 回测参数（commission_rate、stamp_tax_rate、slippage、initial_capital） |
| report | 报告配置（font、font_size、title_font_size） |
| cache | 缓存配置（dir_path、expire_hours） |
| logging | 日志配置（level、format、dir_path） |

**配置加载方式**：

```python
from config import get_settings

settings = get_settings()

# 读取配置
db_url = settings.database.url
redis_url = settings.redis.url
api_port = settings.server.port
```

### 环境配置（.env）

通过 `.env` 文件管理敏感信息，支持多环境配置：

- `.env` — 敏感配置（已加入 `.gitignore`，不提交）
- `.env.example` — 配置模板（提交到仓库）

通过 `ETF_ENV` 环境变量切换当前运行环境（dev / prod）。

## 贡献指南

欢迎对本项目贡献代码或提出改进建议。

### 提交 Issue
- 报告 Bug 时，请描述复现步骤、预期行为和实际表现
- 提出新功能时，请说明使用场景和期望效果

### 代码贡献

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交改动：`git commit -m "feat: add your feature"`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 开发规范
- 遵循 [PEP 8](https://pep8.org/) 编码规范
- 所有函数和类需包含详细的中文文档字符串
- 添加必要的异常处理和日志记录
- 为核心逻辑编写单元测试
- Commit 信息遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范
- 敏感信息（Token、API Key、数据库密码）必须通过 `.env` 文件管理，不得硬编码

## 许可证
MIT