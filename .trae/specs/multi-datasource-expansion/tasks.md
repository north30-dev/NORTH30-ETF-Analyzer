# Tasks

- [x] Task 1: 安全配置管理模块
  - [x] SubTask 1.1: 创建 `etf_analyzer/secure_config.py`，实现 SecureConfig 类，支持从 `.env` 文件和环境变量加载敏感配置，支持多环境（dev/test/prod）配置切换
  - [x] SubTask 1.2: 创建 `.env.example` 模板文件，列出所有需要配置的敏感项（Tushare Token 等），不含真实密钥
  - [x] SubTask 1.3: 修改 `etf_analyzer/config.py`，整合 SecureConfig，移除硬编码敏感信息，添加数据源相关配置项（数据源优先级、健康检查间隔等）
  - [x] SubTask 1.4: 更新 `.gitignore`，确保 `.env`、`.env.local`、`.env.*.local` 被排除

- [x] Task 2: 数据源抽象层与 Akshare 适配
  - [x] SubTask 2.1: 创建 `etf_analyzer/data_sources/` 包目录及 `__init__.py`
  - [x] SubTask 2.2: 创建 `etf_analyzer/data_sources/base.py`，定义 `BaseDataSource` 抽象类，包含 get_realtime_quote、get_history_data、get_etf_list、get_etf_holdings、health_check 抽象方法
  - [x] SubTask 2.3: 创建 `etf_analyzer/data_sources/akshare_source.py`，将现有 `data_fetcher.py` 中的 akshare 逻辑封装为 `AkshareDataSource`，实现 `BaseDataSource` 接口

- [x] Task 3: 新数据源接入
  - [x] SubTask 3.1: 创建 `etf_analyzer/data_sources/tushare_source.py`，实现 `TushareDataSource`，通过 SecureConfig 获取 Token，支持实时行情、历史数据、ETF 列表和持仓信息获取
  - [x] SubTask 3.2: 创建 `etf_analyzer/data_sources/baostock_source.py`，实现 `BaostockDataSource`，支持历史K线数据获取（实时行情标记为不可用）
  - [x] SubTask 3.3: 创建 `etf_analyzer/data_sources/pytdx_source.py`，实现 `PytdxDataSource`，通过通达信接口获取实时行情和历史数据

- [x] Task 4: 数据源管理器
  - [x] SubTask 4.1: 创建 `etf_analyzer/data_source_manager.py`，实现 `DataSourceManager` 类，支持数据源注册、优先级排序、自动故障转移
  - [x] SubTask 4.2: 实现数据源健康检查机制，定期检测各数据源可用性和响应时间，动态调整优先级
  - [x] SubTask 4.3: 修改 `etf_analyzer/data_fetcher.py`，内部委托给 DataSourceManager，保持对外接口不变（get_realtime_quote、get_history_data、get_etf_list、get_etf_holdings）

- [x] Task 5: 智能数据补全模块
  - [x] SubTask 5.1: 创建 `etf_analyzer/data_completion.py`，实现缺失数据智能填充算法（线性插值、前后均值法），补全数据标记来源为"补全"
  - [x] SubTask 5.2: 实现多源数据交叉验证，对比不同数据源同一日数据，差异超阈值标记为"数据冲突"，取中位数
  - [x] SubTask 5.3: 实现数据质量评分机制，基于数据完整性、来源数量、交叉验证一致性计算 0-100 评分

- [x] Task 6: 增量更新模块
  - [x] SubTask 6.1: 创建 `etf_analyzer/incremental_updater.py`，实现增量数据同步，仅获取上次更新日期之后的新数据
  - [x] SubTask 6.2: 实现定时任务自动更新，支持配置更新计划（如每日收盘后执行）
  - [x] SubTask 6.3: 实现数据版本管理，记录每次更新的版本信息（更新时间、数据源、记录数）

- [x] Task 7: 数据异常预警模块
  - [x] SubTask 7.1: 创建 `etf_analyzer/data_monitor.py`，实现数据源健康状态监控，维护各数据源可用性和响应时间记录
  - [x] SubTask 7.2: 实现异常自动告警，数据源连续失败超阈值或质量评分低于阈值时记录 WARNING 日志
  - [x] SubTask 7.3: 实现数据质量报告生成，输出各数据源健康状态、数据完整性统计、补全记录汇总、异常事件列表

- [x] Task 8: 依赖更新与测试
  - [x] SubTask 8.1: 更新 `requirements.txt`，新增 tushare、baostock、pytdx、python-dotenv 依赖
  - [x] SubTask 8.2: 为数据源抽象层编写单元测试（mock 各数据源接口）
  - [x] SubTask 8.3: 为数据源管理器编写单元测试（测试故障转移、优先级切换）
  - [x] SubTask 8.4: 为智能数据补全模块编写单元测试
  - [x] SubTask 8.5: 为安全配置管理模块编写单元测试

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1, Task 2]
- [Task 4] depends on [Task 2, Task 3]
- [Task 5] depends on [Task 4]
- [Task 6] depends on [Task 4]
- [Task 7] depends on [Task 4]
- [Task 8] depends on [Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7]
