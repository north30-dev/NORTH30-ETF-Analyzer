# NORTH30-ETF-Analyzer

命令行 ETF 分析工具，支持多数据源获取、智能数据补全、增量更新与异常预警，提供从数据获取、清洗、分析到可视化与报告生成的全链路能力。

## 功能特性

### 多数据源获取
- **实时行情** — 获取任意 ETF 的最新价格、涨跌幅、成交量等关键指标
- **历史数据** — 支持自定义时间范围的历史K线数据获取，支持前复权/后复权/不复权
- **ETF列表** — 获取全市场 ETF 列表，支持按关键词搜索
- **持仓信息** — 查询 ETF 成分股构成及持仓占比
- **多数据源支持** — 支持 Akshare、Tushare、Baostock、通达信(pytdx) 四种数据源，按优先级自动切换与故障转移
- **安全配置管理** — Token/API Key 通过 `.env` 文件管理，支持 dev/test/prod 多环境配置

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

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| 数据源 | [akshare](https://github.com/akfamily/akshare)、[tushare](https://tushare.pro/)、[baostock](http://baostock.com/)、[pytdx](https://github.com/rainx/pytdx) |
| 配置管理 | [python-dotenv](https://github.com/theskumar/python-dotenv)（.env 多环境配置） |
| 数据处理 | [pandas](https://pandas.pydata.org/)、[numpy](https://numpy.org/) |
| 可视化 | [matplotlib](https://matplotlib.org/)、[mplfinance](https://github.com/matplotlib/mplfinance) |
| 报告生成 | [reportlab](https://www.reportlab.com/)（PDF 生成） |
| 测试框架 | [pytest](https://pytest.org/)、[pytest-cov](https://pytest-cov.readthedocs.io/) |

## 架构设计

```
主入口层
  main.py              命令行交互入口（ETFCLI 类）
      │
模块层
  ┌────────┬────────┬────────┬──────┬──────┐
  │        │        │        │      │      │
数据获取  数据处理  核心分析  可视化 报告生成
  │
  ├── data_source_manager.py   数据源管理器（注册/优先级/故障转移）
  ├── data_sources/            数据源抽象层
  │   ├── base.py              抽象基类 BaseDataSource
  │   ├── akshare_source.py    Akshare 数据源
  │   ├── tushare_source.py    Tushare 数据源
  │   ├── baostock_source.py   Baostock 数据源
  │   └── pytdx_source.py      通达信数据源
  ├── data_completion.py       智能数据补全（缺失填充/交叉验证/质量评分）
  ├── incremental_updater.py   增量更新（版本管理/定时更新）
  └── data_monitor.py          数据异常预警（健康检查/告警/质量报告）
(config.py / logger.py / secure_config.py 为各模块共享)
```

各模块间通过类方法调用形成单向依赖链：
`数据获取 → 数据处理 → 核心分析 → 可视化 → 报告生成`

数据获取层内部架构：
`ETFDataFetcher → DataSourceManager → BaseDataSource 子类（按优先级自动故障转移）`

## 环境要求

- Python 3.9+
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

# 编辑 .env 文件，填入必要的配置（如 Tushare Token）
```

`.env` 配置项说明：

| 配置项 | 必填 | 说明 |
|--------|------|------|
| `ETF_ENV` | 否 | 运行环境：dev / test / prod，默认 dev |
| `TUSHARE_TOKEN` | 否 | Tushare 数据源 Token，不配置则跳过该数据源 |
| `PYTDX_HOST` | 否 | 通达信服务器地址，默认 `119.147.212.81` |
| `PYTDX_PORT` | 否 | 通达信服务器端口，默认 `7709` |
| `DATASOURCE_PRIORITY` | 否 | 数据源优先级，默认 `akshare,tushare,baostock,pytdx` |
| `DATASOURCE_HEALTH_CHECK_INTERVAL` | 否 | 健康检查间隔（秒），默认 `300` |
| `DATASOURCE_FAILURE_THRESHOLD` | 否 | 连续失败告警阈值，默认 `3` |
| `DATA_QUALITY_THRESHOLD` | 否 | 质量评分告警阈值，默认 `60` |
| `CROSS_VALIDATION_THRESHOLD` | 否 | 交叉验证差异阈值（%），默认 `1.0` |

> Akshare 和 Baostock 无需 Token 即可使用；Tushare 需要在 `.env` 中配置 Token。

## 使用指南

### 启动程序

```bash
python main.py
```

### 基本操作流程

程序启动后显示主菜单：

```
========================================
    ETF 分析工具 v1.0
========================================
1. 数据获取
2. 数据分析
3. 数据可视化
4. 报告生成
0. 退出
========================================
请选择操作（输入数字）:
```

### 数据获取

选择主菜单 **1. 数据获取** 进入数据获取子菜单：

```
--- 数据获取 ---
1. 查询ETF列表
2. 获取实时行情
3. 获取历史数据
4. 获取持仓信息
0. 返回主菜单
```

- **查询ETF列表**：输入关键词（如"沪深300"）搜索，直接回车则列出所有 ETF
- **获取实时行情**：输入 6 位 ETF 代码（如 `510300`）
- **获取历史数据**：输入 ETF 代码 + 起始日期（YYYYMMDD）+ 结束日期
- **获取持仓信息**：输入 ETF 代码

### 数据分析

选择主菜单 **2. 数据分析** 进入分析子菜单：

```
--- 数据分析 ---
1. 净值走势分析
2. 成分股构成分析
3. 行业分布统计
4. 风险指标计算
5. 绩效分析
0. 返回主菜单
```

- **净值走势分析**：输入 ETF 代码，输出累计收益率、年化收益率、趋势判断
- **成分股构成分析**：输入 ETF 代码，输出前十大权重股及持仓集中度
- **行业分布统计**：输入 ETF 代码，选择行业分类标准（申万/中信）
- **风险指标计算**：输入 ETF 代码，输出波动率、最大回撤、夏普比率等；可选输入基准代码计算信息比率
- **绩效分析**：输入 ETF 代码 + 基准指数代码，输出超额收益、跟踪误差、胜率

### 数据可视化

选择主菜单 **3. 数据可视化** 进入可视化子菜单：

```
--- 数据可视化 ---
1. K线图
2. 净值走势图
3. 行业分布饼图
4. 成分股权重柱状图
5. 回撤曲线图
0. 返回主菜单
```

每项功能输入 ETF 代码后即生成对应图表，自动保存至 `reports/` 目录，保存路径会显示在控制台中。

### 报告生成

选择主菜单 **4. 报告生成** 进入报告子菜单：

```
--- 报告生成 ---
1. 生成完整分析报告
2. 生成自定义报告
0. 返回主菜单
```

- **完整报告**：输入 ETF 代码，生成包含所有模块的分析报告
- **自定义报告**：输入 ETF 代码后，按提示选择要包含的模块（净值走势、成分股、行业分布、风险指标、绩效分析）

### 常见操作示例

```bash
# 启动程序
python main.py

# 直接查看 ETF 最新行情（通过菜单操作）
# 主菜单 → 1 → 2 → 输入 ETF 代码（如 510300）

# 生成分析报告
# 主菜单 → 4 → 1 → 输入 ETF 代码（如 510300）
# 报告将生成到 reports/ 目录
```

### 运行测试

```bash
# 运行全部单元测试
pytest tests/ -v

# 运行带覆盖率的测试
pytest tests/ -v --cov=etf_analyzer --cov-report=term-missing

# 运行指定测试模块
pytest tests/test_data_source_manager.py -v

# 运行综合功能验证
python tests/test_full_validation.py
```

## 项目目录

```
NORTH30-ETF-Analyzer/
├── main.py                          # 命令行交互入口
├── requirements.txt                 # Python 依赖清单
├── .env.example                     # 环境配置模板
├── .gitignore
├── etf_analyzer/                    # 核心模块包
│   ├── __init__.py
│   ├── config.py                    # 全局配置
│   ├── logger.py                    # 日志模块
│   ├── secure_config.py             # 安全配置管理（.env 多环境）
│   ├── data_fetcher.py              # 数据获取（委托 DataSourceManager）
│   ├── data_source_manager.py       # 数据源管理器（注册/优先级/故障转移）
│   ├── data_sources/                # 数据源抽象层
│   │   ├── __init__.py
│   │   ├── base.py                  # 抽象基类 BaseDataSource
│   │   ├── akshare_source.py        # Akshare 数据源
│   │   ├── tushare_source.py        # Tushare 数据源
│   │   ├── baostock_source.py       # Baostock 数据源
│   │   └── pytdx_source.py          # 通达信数据源
│   ├── data_completion.py           # 智能数据补全
│   ├── incremental_updater.py       # 增量更新
│   ├── data_monitor.py              # 数据异常预警
│   ├── data_processor.py            # 数据处理
│   ├── analyzer.py                  # 核心分析
│   ├── visualizer.py                # 可视化
│   ├── report_generator.py          # 报告生成
│   └── retry.py                     # 重试装饰器
├── tests/                           # 单元测试
│   ├── __init__.py
│   ├── conftest.py                  # 测试 fixtures
│   ├── test_secure_config.py        # 安全配置测试
│   ├── test_data_sources.py         # 数据源抽象层测试
│   ├── test_data_source_manager.py  # 数据源管理器测试
│   ├── test_data_completion.py      # 智能数据补全测试
│   ├── test_data_fetcher.py         # 数据获取测试
│   ├── test_data_processor.py       # 数据处理测试
│   ├── test_analyzer.py             # 核心分析测试
│   └── test_full_validation.py      # 综合功能验证脚本
├── cache/                           # 数据缓存（运行时创建）
├── logs/                            # 日志文件（运行时创建）
└── reports/                         # 报告输出（运行时创建）
```

## 配置文件说明

### 代码配置（config.py）

[config.py](etf_analyzer/config.py) 包含所有可自定义的全局配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `CACHE_DIR` | `"cache"` | 数据缓存目录 |
| `CACHE_EXPIRE_HOURS` | `4` | 缓存过期时间（小时） |
| `DEFAULT_START_DATE` | `"20200101"` | 默认数据起始日期 |
| `RISK_FREE_RATE` | `0.02` | 无风险利率（2%） |
| `SW_INDUSTRY_MAP` | 28个行业 | 申万一级行业分类映射 |
| `ZX_INDUSTRY_MAP` | 30个行业 | 中信一级行业分类映射 |
| `REPORT_DIR` | `"reports"` | 报告输出目录 |
| `LOG_LEVEL` | `"INFO"` | 日志级别 |
| `DATASOURCE_PRIORITY` | `["akshare","tushare","baostock","pytdx"]` | 数据源优先级 |
| `DATASOURCE_HEALTH_CHECK_INTERVAL` | `300` | 健康检查间隔（秒） |
| `DATASOURCE_FAILURE_THRESHOLD` | `3` | 连续失败告警阈值 |
| `DATA_QUALITY_THRESHOLD` | `60` | 质量评分告警阈值 |
| `CROSS_VALIDATION_THRESHOLD` | `1.0` | 交叉验证差异阈值（%） |

### 环境配置（.env）

通过 `.env` 文件管理敏感信息，支持多环境配置：

- `.env` — 基础配置（所有环境共享）
- `.env.dev` — 开发环境覆盖
- `.env.test` — 测试环境覆盖
- `.env.prod` — 生产环境覆盖

通过 `ETF_ENV` 环境变量切换当前运行环境，环境特定配置会覆盖基础配置。

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
- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 编码规范
- 所有函数和类需包含详细的中文文档字符串
- 添加必要的异常处理和日志记录
- 为核心逻辑编写单元测试
- Commit 信息遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范
- 敏感信息（Token、API Key）必须通过 `.env` 文件管理，不得硬编码

## 许可证
MIT
