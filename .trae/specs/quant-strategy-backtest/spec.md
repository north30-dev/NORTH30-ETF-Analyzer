# 量化策略分析与回测框架 Spec

## Why
当前ETF分析工具仅提供基础的数据获取和指标计算能力，缺少量化策略回测与信号生成功能，无法为投资者提供策略验证和决策支持。需要构建完整的量化策略分析与回测框架，扩展专业分析能力。

## What Changes
- 新增策略抽象基类（`etf_analyzer/strategies/base.py`）：定义统一策略接口，所有策略实现该接口
- 新增动量策略（`etf_analyzer/strategies/momentum.py`）：基于价格动量的趋势跟踪策略
- 新增均值回归策略（`etf_analyzer/strategies/mean_reversion.py`）：基于价格偏离均值的反转策略
- 新增行业轮动策略（`etf_analyzer/strategies/sector_rotation.py`）：基于行业动量强弱轮动
- 新增多因子策略（`etf_analyzer/strategies/multi_factor.py`）：基于多因子评分的综合策略
- 新增回测引擎（`etf_analyzer/backtest/engine.py`）：历史数据回测、交易成本模拟、绩效评估
- 新增回测数据加载层（`etf_analyzer/backtest/data_loader.py`）：独立数据加载，支持CSV/数据库/API多源
- 新增参数寻优模块（`etf_analyzer/backtest/optimizer.py`）：网格搜索参数寻优
- 新增信号生成模块（`etf_analyzer/backtest/signals.py`）：买入/卖出信号计算、仓位建议
- 新增策略与回测API路由（`api/routers/strategy.py`、`api/routers/backtest.py`）
- 新增API数据模型（`api/schemas/strategy.py`、`api/schemas/backtest.py`）
- 修改 `requirements.txt`：新增依赖

## Impact
- Affected specs: build-etf-analyzer（新增策略与回测功能扩展核心分析能力）
- Affected code: `etf_analyzer/`（新增strategies和backtest包）、`api/routers/`（新增路由）、`api/schemas/`（新增模型）、`requirements.txt`
- 新增代码: `etf_analyzer/strategies/`、`etf_analyzer/backtest/`、`api/routers/strategy.py`、`api/routers/backtest.py`、`api/schemas/strategy.py`、`api/schemas/backtest.py`

## ADDED Requirements

### Requirement: 策略抽象基类
系统 SHALL 定义统一的策略抽象基类，所有策略必须实现该接口。

#### Scenario: 统一策略接口
- **WHEN** 新增一个策略
- **THEN** 该策略必须继承 `BaseStrategy` 抽象类，实现 `generate_signals`、`get_parameters`、`set_parameters`、`get_name`、`get_description` 方法

#### Scenario: 策略参数管理
- **WHEN** 策略初始化或参数更新
- **THEN** 策略通过 `get_parameters` 返回当前参数字典，通过 `set_parameters` 更新参数，参数变更后自动验证合法性

#### Scenario: 信号输出格式
- **WHEN** 策略执行 `generate_signals` 方法
- **THEN** 返回标准化的信号 DataFrame，包含日期列、信号列（1=买入、-1=卖出、0=持有）、仓位比例列（0.0~1.0）

### Requirement: 动量策略
系统 SHALL 提供基于价格动量的趋势跟踪策略。

#### Scenario: 动量信号生成
- **WHEN** 用户对ETF历史数据执行动量策略
- **THEN** 系统基于N日收益率动量指标生成买入/卖出信号，当动量值超过上阈值时产生买入信号，低于下阈值时产生卖出信号

#### Scenario: 参数配置
- **WHEN** 用户配置动量策略参数
- **THEN** 支持配置的参数包括：动量周期（默认20日）、买入阈值（默认0.02）、卖出阈值（默认-0.02）

#### Scenario: 多周期动量
- **WHEN** 用户启用多周期动量模式
- **THEN** 系统同时计算短周期和长周期动量，仅在两者方向一致时产生信号，减少假信号

### Requirement: 均值回归策略
系统 SHALL 提供基于价格偏离均值的反转策略。

#### Scenario: 均值回归信号生成
- **WHEN** 用户对ETF历史数据执行均值回归策略
- **THEN** 系统基于布林带或Z-Score指标生成信号，价格触及下轨时产生买入信号，触及上轨时产生卖出信号

#### Scenario: 参数配置
- **WHEN** 用户配置均值回归策略参数
- **THEN** 支持配置的参数包括：均线周期（默认20日）、标准差倍数（默认2.0）、入场阈值（默认2.0）

#### Scenario: 均值回归出场
- **WHEN** 价格回归至均值附近
- **THEN** 系统产生平仓信号（信号=0），建议将仓位恢复至中性水平

### Requirement: 行业轮动策略
系统 SHALL 提供基于行业动量强弱的轮动策略。

#### Scenario: 行业动量排名
- **WHEN** 用户对一组行业ETF执行行业轮动策略
- **THEN** 系统计算各行业ETF的动量得分，按得分降序排名

#### Scenario: 轮动信号生成
- **WHEN** 行业动量排名完成
- **THEN** 系统对排名前N的行业ETF产生买入信号，对已持有但排名跌出前M的ETF产生卖出信号

#### Scenario: 参数配置
- **WHEN** 用户配置行业轮动策略参数
- **THEN** 支持配置的参数包括：动量周期（默认20日）、持仓数量（默认3）、调仓频率（默认月度）

### Requirement: 多因子策略
系统 SHALL 提供基于多因子评分的综合策略。

#### Scenario: 因子计算
- **WHEN** 用户对ETF执行多因子策略
- **THEN** 系统计算多个因子得分，包括：动量因子、波动率因子、成交量因子、趋势因子

#### Scenario: 综合评分与信号
- **WHEN** 各因子得分计算完成
- **THEN** 系统按配置的因子权重计算综合评分，评分超过买入阈值时产生买入信号，低于卖出阈值时产生卖出信号

#### Scenario: 参数配置
- **WHEN** 用户配置多因子策略参数
- **THEN** 支持配置的参数包括：因子权重字典、买入阈值（默认0.6）、卖出阈值（默认0.4）、评分窗口（默认20日）

### Requirement: 回测数据加载层
系统 SHALL 提供独立的数据加载层，支持多种数据源。

#### Scenario: 从API加载数据
- **WHEN** 用户选择API数据源
- **THEN** 系统通过现有数据源管理器获取ETF历史数据，转换为回测引擎所需的标准化格式

#### Scenario: 从CSV文件加载数据
- **WHEN** 用户指定CSV文件路径
- **THEN** 系统读取CSV文件，自动识别列名映射（日期、开盘、最高、最低、收盘、成交量），转换为标准格式

#### Scenario: 从数据库加载数据
- **WHEN** 用户选择数据库数据源
- **THEN** 系统从MySQL数据库读取历史数据缓存，转换为回测引擎所需的标准化格式

#### Scenario: 数据格式标准化
- **WHEN** 数据加载完成
- **THEN** 输出的DataFrame包含统一列名：date、open、high、low、close、volume，按日期升序排列，无缺失值

### Requirement: 回测引擎
系统 SHALL 提供历史数据回测引擎，支持策略回测和绩效评估。

#### Scenario: 单策略回测
- **WHEN** 用户指定策略、ETF代码和时间范围执行回测
- **THEN** 系统按时间顺序逐日模拟策略信号，根据信号执行虚拟交易，记录每笔交易和每日持仓

#### Scenario: 交易成本模拟
- **WHEN** 回测执行交易
- **THEN** 系统按配置扣除交易成本，支持设置佣金费率（默认万三）、印花税（卖出千一）、滑点（默认0.1%）

#### Scenario: 多策略对比回测
- **WHEN** 用户同时指定多个策略进行回测
- **THEN** 系统在相同数据条件下分别执行各策略回测，返回各策略的绩效指标，支持横向对比

#### Scenario: 绩效评估指标
- **WHEN** 回测完成
- **THEN** 系统计算并返回以下绩效指标：总收益率、年化收益率、夏普比率、最大回撤、最大回撤持续天数、胜率、盈亏比、交易次数、Calmar比率

#### Scenario: 回测结果输出
- **WHEN** 回测完成
- **THEN** 系统返回结构化的回测结果，包含：绩效指标字典、交易记录DataFrame、每日净值曲线DataFrame、持仓变化记录

### Requirement: 参数寻优
系统 SHALL 提供基于网格搜索的策略参数寻优功能。

#### Scenario: 网格搜索
- **WHEN** 用户指定策略、参数范围和步长
- **THEN** 系统遍历参数组合，对每组参数执行回测，记录绩效指标

#### Scenario: 寻优结果排序
- **WHEN** 网格搜索完成
- **THEN** 系统按指定指标（默认夏普比率）对参数组合排序，返回最优参数组合及Top N结果

#### Scenario: 参数范围配置
- **WHEN** 用户配置寻优参数
- **THEN** 支持为每个参数指定搜索范围（起始值、结束值、步长），支持整数和浮点数参数

### Requirement: 信号生成模块
系统 SHALL 提供独立的信号生成和仓位建议功能。

#### Scenario: 实时信号计算
- **WHEN** 用户请求某ETF的策略信号
- **THEN** 系统基于最新数据和策略参数计算当前信号（买入/卖出/持有）及建议仓位比例

#### Scenario: 仓位建议
- **WHEN** 策略产生信号
- **THEN** 系统根据信号强度和风险指标给出仓位建议：买入信号建议仓位0.3~1.0，卖出信号建议减仓至0~0.3，持有信号维持当前仓位

#### Scenario: 策略执行报告
- **WHEN** 用户请求策略执行报告
- **THEN** 系统生成包含当前信号、历史信号统计、近期交易建议、风险提示的结构化报告

### Requirement: 策略API接口
系统 SHALL 通过FastAPI暴露策略管理和信号生成的RESTful接口。

#### Scenario: 获取策略列表
- **WHEN** 客户端发送 GET /api/v1/strategy/list 请求
- **THEN** 返回所有可用策略的名称、描述和默认参数

#### Scenario: 获取策略参数
- **WHEN** 客户端发送 GET /api/v1/strategy/{strategy_name}/params 请求
- **THEN** 返回指定策略的当前参数和参数说明

#### Scenario: 更新策略参数
- **WHEN** 客户端发送 PUT /api/v1/strategy/{strategy_name}/params 请求
- **THEN** 更新指定策略的参数，返回更新后的参数

#### Scenario: 生成交易信号
- **WHEN** 客户端发送 POST /api/v1/strategy/{strategy_name}/signals 请求（含ETF代码和日期范围）
- **THEN** 返回策略生成的交易信号序列

### Requirement: 回测API接口
系统 SHALL 通过FastAPI暴露回测执行和结果查询的RESTful接口。

#### Scenario: 执行回测
- **WHEN** 客户端发送 POST /api/v1/backtest/run 请求（含策略名、ETF代码、日期范围、参数）
- **THEN** 执行回测并返回回测结果ID和绩效指标摘要

#### Scenario: 查询回测结果
- **WHEN** 客户端发送 GET /api/v1/backtest/{backtest_id}/result 请求
- **THEN** 返回回测的完整结果，包括绩效指标、交易记录、净值曲线

#### Scenario: 多策略对比
- **WHEN** 客户端发送 POST /api/v1/backtest/compare 请求（含多个策略名）
- **THEN** 返回多策略回测对比结果

#### Scenario: 参数寻优
- **WHEN** 客户端发送 POST /api/v1/backtest/optimize 请求（含策略名、参数范围）
- **THEN** 执行网格搜索并返回最优参数组合

#### Scenario: 获取回测历史
- **WHEN** 客户端发送 GET /api/v1/backtest/history 请求
- **THEN** 返回历史回测记录列表，支持按策略名、ETF代码筛选

## MODIFIED Requirements

### Requirement: 核心分析模块
系统 SHALL 在现有分析功能基础上，支持与策略模块的协同工作。

#### Scenario: 策略使用分析指标
- **WHEN** 策略需要计算技术指标
- **THEN** 策略模块可复用 ETFAnalyzer 中已有的风险指标、收益率计算等能力，避免重复实现
