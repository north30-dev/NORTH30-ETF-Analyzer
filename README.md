# ETF Analyzer

基于 [akshare](https://github.com/akfamily/akshare) 开发的命令行 ETF 分析工具，提供从数据获取、清洗、分析到可视化与报告生成的全链路能力。

## 功能特性

### 数据获取
- **实时行情** — 获取任意 ETF 的最新价格、涨跌幅、成交量等关键指标
- **历史数据** — 支持自定义时间范围的历史K线数据获取，支持前复权/后复权/不复权
- **ETF列表** — 获取全市场 ETF 列表，支持按关键词搜索
- **持仓信息** — 查询 ETF 成分股构成及持仓占比

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
| 数据源 | [akshare](https://github.com/akfamily/akshare)（开源金融数据接口库） |
| 数据处理 | [pandas](https://pandas.pydata.org/)、[numpy](https://numpy.org/) |
| 可视化 | [matplotlib](https://matplotlib.org/)、[mplfinance](https://github.com/matplotlib/mplfinance) |
| 报告生成 | [reportlab](https://www.reportlab.com/)（PDF 生成） |
| 测试框架 | [pytest](https://pytest.org/) |

## 架构设计

```
主入口层
  main.py         命令行交互入口（ETFCLI 类）
      │
模块层
  ┌─────┬─────┬──────┬──────┬──────┐
  │     │     │      │      │      │
数据获取 数据处理 核心分析 可视化 报告生成
(config.py / logger.py 为各模块共享)
```

各模块间通过类方法调用形成单向依赖链：
`数据获取 → 数据处理 → 核心分析 → 可视化 → 报告生成`

## 环境要求

- Python 3.9+
- Windows / macOS / Linux
- 网络连接（用于通过 akshare 获取金融数据）

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-username/etf-analyzer.git
cd etf-analyzer
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
# 运行全部测试
pytest tests/ -v

# 运行指定测试模块
pytest tests/test_data_processor.py -v
```

## 项目目录

```
ETF-Analyzer/
├── main.py                          # 命令行交互入口
├── requirements.txt                 # Python 依赖清单
├── .gitignore
├── etf_analyzer/                    # 核心模块包
│   ├── __init__.py
│   ├── config.py                    # # 全局配置
│   ├── logger.py                    # 日志模块
│   ├── data_fetcher.py              # 数据获取
│   ├── data_processor.py            # 数据处理
│   ├── analyzer.py                  # 核心分析
│   ├── visualizer.py                # 可视化
│   └── report_generator.py          # 报告生成
├── tests/                           # 单元测试
│   ├── __init__.py
│   ├── conftest.py                  # 测试 fixtures
│   ├── test_data_fetcher.py         # 数据获取测试（11 个）
│   ├── test_data_processor.py       # 数据处理测试（15 个）
│   └── test_analyzer.py             # 核心分析测试（6 个）
├── cache/                           # 数据缓存（运行时创建）
├── logs/                            # 日志文件（运行时创建）
└── reports/                         # 报告输出（运行时创建）
```

## 配置文件说明

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

## 许可证

[MIT](LICENSE)