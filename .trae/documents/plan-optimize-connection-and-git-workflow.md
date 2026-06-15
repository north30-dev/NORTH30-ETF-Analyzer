# 优化 /plan 工作流：连接稳定性与Git操作

## 概述
`/plan` 命令（Trae IDE内置）触发ETF分析工作流，该工作流依赖 `akshare` 库通过HTTP请求访问中国金融数据API。这些请求因网络不稳定频繁出现 `Connection aborted` 和 `RemoteDisconnected` 错误；同时，高频请求容易触发API服务端的IP封禁策略。本计划通过以下方式优化流程：(1) 在执行前增加Git工作流（拉取main → 创建新分支）；(2) 实现带**随机抖动(jitter)和全局速率限制**的重试逻辑，防止IP被封；(3) 在继续后续操作前验证每个步骤是否成功。

## 当前状态分析
- **入口点**: [main.py](file:///e:/Project/PythonProject/ETF-Analyzer/main.py) — CLI调用 `ETFDataFetcher` 方法，内部调用 `akshare` API。
- **数据获取**: [data_fetcher.py](file:///e:/Project/PythonProject/ETF-Analyzer/etf_analyzer/data_fetcher.py) — 所有 `ak.` 调用（`fund_etf_spot_em`、`fund_etf_hist_em`、`fund_etf_hold_em`、`tool_trade_date_hist_sina`）仅被简单的 `try/except Exception` 包裹，**没有重试逻辑**。
- **分析器**: [analyzer.py](file:///e:/Project/PythonProject/ETF-Analyzer/etf_analyzer/analyzer.py) — 也进行 `ak.` 调用（`stock_individual_info_em`、`index_zh_a_hist`、`stock_zh_index_daily`），同样**没有重试逻辑**。
- **Git**: 远程库 `origin` 位于 `github.com/north30-dev/NORTH30-ETF-Analyzer.git`。当前分支为 `main`。
- **不存在预运行脚本**或Git工作流自动化。

## 拟修改的方案

### 1. 新增重试与速率限制工具模块 (`etf_analyzer/retry.py`) — 新建文件
**内容**: 提供两个核心工具：(A) 带随机抖动的指数退避重试装饰器；(B) 全局速率限制器，防止高频请求被封IP。
**原因**: 金融数据API对同一IP的请求频率极为敏感，必须同时解决连接不稳定和反爬策略两个问题。

**实现方式 (A) — 重试装饰器 `@retry`**:
- 默认参数 `max_attempts=3, base_delay=2.0, max_delay=60.0, jitter=0.5`
- 每次重试的实际等待时间：`delay = min(base_delay * 2^(attempt-1), max_delay)`
- 加入**随机抖动**：`actual_delay = delay * random.uniform(1 - jitter, 1 + jitter)`（jitter=0.5 表示在50%~150%范围随机），避免多个重试发在同一时刻
- 捕获的网络异常（按优先级）：
  - `requests.exceptions.ConnectionError`（含 `Connection aborted`）
  - `urllib3.exceptions.ProtocolError`（`RemoteDisconnected` 的父类）
  - `requests.exceptions.Timeout`
- 每次重试时通过 logger 记录警告日志（含尝试次数、等待秒数、异常消息）
- 所有重试耗尽后，重新抛出最后一次异常

**实现方式 (B) — 全局速率限制器 `RateLimiter`**:
- 使用 ` threading.Lock` 保护，类级别的单例（在模块作用域内实例化）
- 核心参数：`min_interval=1.5`（相邻请求最小间隔1.5秒）
- 每次调用 `acquire()` 时：
  - 计算离上次请求的时间差
  - 如果时间差 < min_interval，sleep 剩余时间
  - 更新上次请求时间戳
- 在 `ETFDataFetcher.__init__` 和 `ETFAnalyzer.__init__` 中共享同一个速率限制器实例
- 额外支持 `consecutive_failures` 计数：当连续失败次数 >= 2 时，自动将 `min_interval` 临时提升至 3秒，并在连续失败达到 3次时建议用户等待

### 2. 对 `data_fetcher.py` 中所有网络调用应用重试与限速 — 修改文件
**内容**: 用重试装饰器包裹所有 `ak.` 函数调用，并在调用前通过速率限制器控制请求频率。
**原因**: 这些是连接错误和IP封禁风险的主要来源。
**涉及文件/修改**:
- [data_fetcher.py](file:///e:/Project/PythonProject/ETF-Analyzer/etf_analyzer/data_fetcher.py):
  - 导入 `retry` 装饰器和 `rate_limiter` 实例
  - `get_realtime_quote()`: 调用 `ak.fund_etf_spot_em()` 前先 `rate_limiter.acquire()`，用 `@retry` 包裹
  - `get_history_data()`: 同上，对 `ak.fund_etf_hist_em()` 应用
  - `get_etf_list()`: 同上，对 `ak.fund_etf_spot_em()` 应用
  - `get_etf_holdings()`: 同上，对 `ak.fund_etf_hold_em()` 应用
  - `_adjust_trading_day()`: 同上，对 `ak.tool_trade_date_hist_sina()` 应用
- **模式**: 保留现有的 `try/except` 作为外部保护；在内部对具体的 `ak.` 调用增加重试和限速。

### 3. 对 `analyzer.py` 中网络调用应用重试与限速 — 修改文件
**内容**: 用重试装饰器包裹所有 `ak.` 函数调用，并通过速率限制器控制请求频率。
**原因**: `_get_industry_from_stock_codes()` 会逐个股票调用API，**极易触发高频封禁**，必须严格限速。
**涉及文件/修改**:
- [analyzer.py](file:///e:/Project/PythonProject/ETF-Analyzer/etf_analyzer/analyzer.py):
  - 导入 `retry` 装饰器和 `rate_limiter` 实例
  - `_get_industry_from_stock_codes()` 中，对每次 `ak.stock_individual_info_em()` 调用应用 `@retry` **和** `rate_limiter.acquire()`
  - `_get_benchmark_data()`: 对 `ak.index_zh_a_hist()` 和 `ak.stock_zh_index_daily()` 应用

### 4. 添加Git前置检查与分支创建 — 修改 `main.py`
**内容**: 在CLI菜单启动前，增加一个可选的Git工作流，执行以下操作：
1. 检查 `git` 是否可用
2. 从 `origin/main` 拉取最新代码（网络失败时带重试，使用 retry 模块）
3. 基于 `main` 创建一个带时间戳的新本地分支（例如 `feat/plan-run-20260615-1430`）
4. 验证分支创建成功后再继续
**原因**: 确保分析在最新代码上运行，且所有修改隔离到专用分支。
**实现方式**:
- 在 `ETFCLI` 类中新增 `_git_preflight()` 方法
- 在 `run()` 开始时调用（或通过CLI标志 `--auto-branch` 控制）
- 使用 `subprocess.run` 并设置 `check=True`，捕获输出
- Git拉取失败时（如无网络），打印清晰警告并提示用户是否在不拉取的情况下继续
- 分支创建失败时，打印错误并中止（因为后续操作依赖新分支）
- 通过运行 `git branch --show-current` 验证分支创建成功

### 5. 更新 `.gitignore` — 按需修改
**内容**: 确保生成的临时文件不会被意外提交。
**文件**: [.gitignore](file:///e:/Project/PythonProject/ETF-Analyzer/.gitignore)
**操作**: 读取现有内容，如有缺失则补充条目（如 `__pycache__/`、`*.pkl`、`reports/`、`logs/`、`cache/`）。

## 假设与决策
- **重试策略保守**：最多重试3次，起始等待2秒（带50%随机抖动），最大等待60秒。既保证恢复机会，又避免密集重试触发封禁。
- **全局速率限制**：所有 `ak.` 调用共享同一个 `RateLimiter` 实例，最小间隔1.5秒。连续失败时自动降频至3秒间隔。
- **Git拉取失败不阻塞**：如果拉取失败（如无网络），警告用户后继续使用本地已有代码。
- **分支创建失败则阻塞**：如果无法创建新分支，提示用户手动处理，不自动继续。
- **akshare异常**：`akshare` 内部使用 `requests`/`urllib3`，捕获 `requests.exceptions.ConnectionError` 和 `urllib3.exceptions.ProtocolError` 即可覆盖 `RemoteDisconnected`。

## 验证步骤
1. 运行 `python -c "from etf_analyzer.retry import retry, rate_limiter; print('retry模块加载成功')"` 验证导入
2. 运行 `python main.py` 并观察Git前置检查输出（拉取 + 分支创建）
3. 有意断开网络，执行数据获取操作，验证重试消息出现且优雅降级
4. 观察速率限制效果：连续请求时应至少间隔1.5秒
5. 通过 `git branch --list` 验证新分支存在
6. 运行现有测试套件：`python -m pytest tests/ -v`