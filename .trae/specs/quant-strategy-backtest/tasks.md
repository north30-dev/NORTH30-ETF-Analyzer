# Tasks

- [x] Task 1: 创建策略抽象基类与策略包结构
  - [x] SubTask 1.1: 创建 `etf_analyzer/strategies/__init__.py`，注册策略工厂
  - [x] SubTask 1.2: 创建 `etf_analyzer/strategies/base.py`，定义 BaseStrategy 抽象基类（generate_signals、get_parameters、set_parameters、get_name、get_description）
  - [x] SubTask 1.3: 定义标准化信号输出格式（DataFrame：date、signal、position）

- [x] Task 2: 实现动量策略
  - [x] SubTask 2.1: 创建 `etf_analyzer/strategies/momentum.py`，实现 MomentumStrategy
  - [x] SubTask 2.2: 实现N日动量计算与信号生成逻辑
  - [x] SubTask 2.3: 实现多周期动量模式（短周期+长周期一致性过滤）

- [x] Task 3: 实现均值回归策略
  - [x] SubTask 3.1: 创建 `etf_analyzer/strategies/mean_reversion.py`，实现 MeanReversionStrategy
  - [x] SubTask 3.2: 实现布林带/Z-Score指标计算与信号生成
  - [x] SubTask 3.3: 实现均值回归出场逻辑（价格回归均值时平仓）

- [x] Task 4: 实现行业轮动策略
  - [x] SubTask 4.1: 创建 `etf_analyzer/strategies/sector_rotation.py`，实现 SectorRotationStrategy
  - [x] SubTask 4.2: 实现多行业ETF动量排名与轮动信号生成
  - [x] SubTask 4.3: 实现调仓频率控制（月度/周度）

- [x] Task 5: 实现多因子策略
  - [x] SubTask 5.1: 创建 `etf_analyzer/strategies/multi_factor.py`，实现 MultiFactorStrategy
  - [x] SubTask 5.2: 实现动量因子、波动率因子、成交量因子、趋势因子计算
  - [x] SubTask 5.3: 实现加权综合评分与信号生成

- [x] Task 6: 实现回测数据加载层
  - [x] SubTask 6.1: 创建 `etf_analyzer/backtest/__init__.py`
  - [x] SubTask 6.2: 创建 `etf_analyzer/backtest/data_loader.py`，实现 BacktestDataLoader 类
  - [x] SubTask 6.3: 实现API数据源加载（复用现有数据源管理器）
  - [x] SubTask 6.4: 实现CSV文件数据源加载（自动列名映射）
  - [x] SubTask 6.5: 实现数据库数据源加载（从MySQL缓存读取）
  - [x] SubTask 6.6: 实现数据格式标准化（统一列名：date/open/high/low/close/volume）

- [x] Task 7: 实现回测引擎
  - [x] SubTask 7.1: 创建 `etf_analyzer/backtest/engine.py`，实现 BacktestEngine 类
  - [x] SubTask 7.2: 实现逐日模拟回测逻辑（信号驱动交易执行）
  - [x] SubTask 7.3: 实现交易成本模拟（佣金、印花税、滑点）
  - [x] SubTask 7.4: 实现绩效评估指标计算（总收益率、年化收益率、夏普比率、最大回撤、胜率、盈亏比、Calmar比率等）
  - [x] SubTask 7.5: 实现多策略对比回测功能
  - [x] SubTask 7.6: 实现回测结果结构化输出（绩效指标、交易记录、净值曲线、持仓变化）

- [x] Task 8: 实现参数寻优模块
  - [x] SubTask 8.1: 创建 `etf_analyzer/backtest/optimizer.py`，实现 GridSearchOptimizer 类
  - [x] SubTask 8.2: 实现参数网格生成与遍历
  - [x] SubTask 8.3: 实现寻优结果排序（按指定指标，默认夏普比率）

- [x] Task 9: 实现信号生成模块
  - [x] SubTask 9.1: 创建 `etf_analyzer/backtest/signals.py`，实现 SignalGenerator 类
  - [x] SubTask 9.2: 实现实时信号计算与仓位建议
  - [x] SubTask 9.3: 实现策略执行报告生成

- [x] Task 10: 实现策略与回测API接口
  - [x] SubTask 10.1: 创建 `api/schemas/strategy.py`，定义策略相关请求/响应模型
  - [x] SubTask 10.2: 创建 `api/schemas/backtest.py`，定义回测相关请求/响应模型
  - [x] SubTask 10.3: 创建 `api/routers/strategy.py`，实现策略管理API（列表、参数查询/更新、信号生成）
  - [x] SubTask 10.4: 创建 `api/routers/backtest.py`，实现回测API（执行回测、查询结果、多策略对比、参数寻优、回测历史）
  - [x] SubTask 10.5: 在 `api/main.py` 中注册新路由

- [x] Task 11: 更新依赖与配置
  - [x] SubTask 11.1: 更新 `requirements.txt`，确认无需新增额外依赖（回测框架基于pandas/numpy实现）
  - [x] SubTask 11.2: 在 `config/default.yaml` 中新增策略与回测相关配置项

- [x] Task 12: 编写单元测试
  - [x] SubTask 12.1: 编写策略基类和4个策略的单元测试
  - [x] SubTask 12.2: 编写回测引擎和数据加载层的单元测试
  - [x] SubTask 12.3: 编写参数寻优和信号生成的单元测试
  - [x] SubTask 12.4: 编写API接口的集成测试

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 1]
- [Task 5] depends on [Task 1]
- [Task 7] depends on [Task 6]
- [Task 8] depends on [Task 7]
- [Task 9] depends on [Task 1]
- [Task 10] depends on [Task 7, Task 8, Task 9]
- [Task 12] depends on [Task 10, Task 11]
- Task 2, 3, 4, 5 可并行实现
- Task 6, 9 可并行实现
