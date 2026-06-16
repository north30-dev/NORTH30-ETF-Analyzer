# 多数据源扩展与智能数据补全 Spec

## Why
当前 ETF 分析工具仅依赖 akshare 单一数据源，一旦该数据源服务不稳定或接口变更，将导致数据获取失败，影响整个分析流程。需要扩展多数据源支持、实现智能数据补全和质量校验，提升数据获取的可靠性和数据质量。

## What Changes
- 新增数据源抽象层（`data_sources/`）：定义统一数据源接口，支持 akshare、Tushare、Baostock、pytdx 四种数据源
- 新增数据源管理器（`data_source_manager.py`）：实现数据源自动切换、故障转移、优先级排序
- 新增智能数据补全模块（`data_completion.py`）：缺失数据智能填充、多源交叉验证、数据质量评分
- 新增增量更新模块（`incremental_updater.py`）：历史数据增量同步、定时任务自动更新、数据版本管理
- 新增数据异常预警模块（`data_monitor.py`）：数据源健康监控、异常自动告警、数据质量报告
- 新增安全配置管理（`secure_config.py`）：统一管理 Token/API Key 等敏感信息，支持多环境配置
- 新增配置文件（`.env.example`、`config/settings.py`）：环境变量模板与多环境配置加载
- 修改现有 `data_fetcher.py`：基于数据源抽象层重构，保持对外接口不变
- 修改现有 `config.py`：整合安全配置管理，移除硬编码敏感信息
- 修改 `requirements.txt`：新增 tushare、baostock、pytdx、python-dotenv 等依赖

## Impact
- Affected specs: build-etf-analyzer（数据获取模块需求变更）
- Affected code: `etf_analyzer/data_fetcher.py`、`etf_analyzer/config.py`、`requirements.txt`
- 新增代码: `etf_analyzer/data_sources/`、`etf_analyzer/data_source_manager.py`、`etf_analyzer/data_completion.py`、`etf_analyzer/incremental_updater.py`、`etf_analyzer/data_monitor.py`、`etf_analyzer/secure_config.py`

## ADDED Requirements

### Requirement: 安全配置管理
系统 SHALL 提供统一的敏感信息管理机制，Token、API Key 等敏感信息通过配置文件管理，不得硬编码在源代码中。

#### Scenario: 从环境变量加载敏感配置
- **WHEN** 系统启动并初始化配置
- **THEN** 从 `.env` 文件或系统环境变量中读取 Tushare Token、API Key 等敏感信息，不暴露在源代码中

#### Scenario: 多环境配置支持
- **WHEN** 在不同环境（开发、测试、生产）下运行系统
- **THEN** 通过 `ETF_ENV` 环境变量或 `.env.{env}` 文件加载对应环境的配置，各环境配置互不干扰

#### Scenario: 配置缺失告警
- **WHEN** 必需的敏感配置项（如 Tushare Token）缺失
- **THEN** 系统在启动时输出明确的告警日志，提示用户配置缺失，该数据源标记为不可用但不影响其他数据源

#### Scenario: 配置文件安全
- **WHEN** 项目提交到版本控制系统
- **THEN** `.env` 文件被 `.gitignore` 排除，仅提交 `.env.example` 模板文件，模板中不含真实密钥

### Requirement: 数据源抽象层
系统 SHALL 定义统一的数据源接口，所有数据源实现该接口，确保可互换使用。

#### Scenario: 统一接口定义
- **WHEN** 新增一个数据源
- **THEN** 该数据源必须实现 `BaseDataSource` 抽象类定义的所有方法（get_realtime_quote、get_history_data、get_etf_list、get_etf_holdings、health_check）

#### Scenario: Akshare 数据源适配
- **WHEN** 系统使用 akshare 数据源
- **THEN** 现有 akshare 数据获取逻辑被封装为 `AkshareDataSource`，行为与重构前一致

#### Scenario: Tushare 数据源接入
- **WHEN** 用户配置了有效的 Tushare Token
- **THEN** 系统可通过 Tushare 数据源获取 ETF 实时行情、历史数据、ETF 列表和持仓信息

#### Scenario: Baostock 数据源接入
- **WHEN** 系统使用 Baostock 数据源
- **THEN** 系统可通过 Baostock 获取 ETF 历史K线数据（Baostock 无实时行情接口，该功能返回不可用标记）

#### Scenario: pytdx 数据源接入
- **WHEN** 系统使用 pytdx 数据源
- **THEN** 系统可通过通达信接口获取 ETF 实时行情和历史数据

### Requirement: 数据源自动切换与故障转移
系统 SHALL 在数据源不可用时自动切换到备选数据源。

#### Scenario: 自动故障转移
- **WHEN** 主数据源请求失败（网络异常、接口超时、返回空数据）
- **THEN** 系统自动按优先级切换到下一个可用数据源重试请求

#### Scenario: 数据源优先级配置
- **WHEN** 用户配置了数据源优先级列表（如 akshare > tushare > baostock > pytdx）
- **THEN** 系统按配置的优先级顺序尝试数据源

#### Scenario: 数据源健康检查
- **WHEN** 系统定期执行数据源健康检查
- **THEN** 记录每个数据源的响应时间和可用状态，动态调整优先级

#### Scenario: 全部数据源不可用
- **WHEN** 所有配置的数据源均不可用
- **THEN** 系统返回空数据并记录 ERROR 日志，提示用户检查网络或数据源配置

### Requirement: 智能数据补全
系统 SHALL 对缺失数据进行智能填充和交叉验证。

#### Scenario: 缺失数据智能填充
- **WHEN** 某数据源返回的历史数据存在日期缺失（非交易日除外）
- **THEN** 系统使用线性插值或前后均值法智能填充缺失数据点，并在数据中标记为"补全数据"

#### Scenario: 多源数据交叉验证
- **WHEN** 多个数据源返回同一 ETF 的同一日数据
- **THEN** 系统对比各数据源数据，若差异超过阈值（默认 1%）则标记为"数据冲突"，取中位数作为最终值

#### Scenario: 数据质量评分
- **WHEN** 数据经过补全和交叉验证后
- **THEN** 系统为每条数据计算质量评分（0-100），评分依据包括数据完整性、来源数量、交叉验证一致性

### Requirement: 增量更新机制
系统 SHALL 支持历史数据的增量同步和定时自动更新。

#### Scenario: 增量数据同步
- **WHEN** 用户请求更新某 ETF 的历史数据
- **THEN** 系统仅获取上次更新日期之后的新数据，与已有数据合并，避免全量重复获取

#### Scenario: 定时任务自动更新
- **WHEN** 用户配置了定时更新计划（如每日收盘后 16:00）
- **THEN** 系统按计划自动执行数据更新任务

#### Scenario: 数据版本管理
- **WHEN** 数据被更新或补全后
- **THEN** 系统记录数据版本信息（更新时间、数据源、记录数），支持查询历史版本摘要

### Requirement: 数据异常预警
系统 SHALL 实时监控数据源健康状态并自动告警。

#### Scenario: 数据源健康监控
- **WHEN** 系统运行过程中
- **THEN** 定期检查各数据源的可用性和响应时间，维护健康状态记录

#### Scenario: 数据异常自动告警
- **WHEN** 数据源连续失败次数超过阈值（默认 3 次）或数据质量评分低于阈值（默认 60 分）
- **THEN** 系统记录 WARNING 日志，包含数据源名称、失败原因、建议操作

#### Scenario: 数据质量报告生成
- **WHEN** 用户请求生成数据质量报告
- **THEN** 系统输出包含各数据源健康状态、数据完整性统计、补全记录汇总、异常事件列表的报告

## MODIFIED Requirements

### Requirement: 数据获取模块
系统 SHALL 通过数据源管理器获取 ETF 数据，对外接口保持不变，内部实现支持多数据源自动切换。

#### Scenario: 获取实时行情数据
- **WHEN** 用户请求某 ETF 的实时行情
- **THEN** 系统通过数据源管理器按优先级尝试各数据源，返回最新价格、涨跌幅、成交量等指标

#### Scenario: 获取历史数据
- **WHEN** 用户指定 ETF 代码和时间范围
- **THEN** 系统通过数据源管理器获取数据，优先使用缓存，缓存未命中时按优先级尝试各数据源

#### Scenario: 数据缓存
- **WHEN** 用户重复请求相同数据且缓存未过期
- **THEN** 系统直接返回缓存数据，不发起网络请求（行为不变）
