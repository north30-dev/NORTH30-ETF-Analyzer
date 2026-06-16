# Tasks

- [ ] Task 1: 更新 etf_analyzer/__init__.py 重新导出核心类
  - [ ] SubTask 1.1: 编写 __init__.py 内容，从 core/、services/、utils/ 子包重新导出所有公开类和函数
  - [ ] SubTask 1.2: 更新 core/__init__.py、services/__init__.py、utils/__init__.py 重新导出各自子包的公开接口

- [ ] Task 2: 在旧文件位置创建兼容层
  - [ ] SubTask 2.1: 创建 etf_analyzer/analyzer.py 兼容层（从 core.analyzer 重导出 ETFAnalyzer）
  - [ ] SubTask 2.2: 创建 etf_analyzer/data_fetcher.py 兼容层（从 core.data_fetcher 重导出 ETFDataFetcher）
  - [ ] SubTask 2.3: 创建 etf_analyzer/data_processor.py 兼容层（从 core.data_processor 重导出 DataProcessor）
  - [ ] SubTask 2.4: 创建 etf_analyzer/visualizer.py 兼容层（从 core.visualizer 重导出 ETFVisualizer）
  - [ ] SubTask 2.5: 创建 etf_analyzer/report_generator.py 兼容层（从 core.report_generator 重导出 ReportGenerator, AVAILABLE_MODULES, MODULE_TITLES）
  - [ ] SubTask 2.6: 创建 etf_analyzer/data_source_manager.py 兼容层（从 services.data_source_manager 重导出 DataSourceManager）
  - [ ] SubTask 2.7: 创建 etf_analyzer/data_completion.py 兼容层（从 services.data_completion 重导出 DataCompletion）
  - [ ] SubTask 2.8: 创建 etf_analyzer/incremental_updater.py 兼容层（从 services.incremental_updater 重导出 IncrementalUpdater）
  - [ ] SubTask 2.9: 创建 etf_analyzer/data_monitor.py 兼容层（从 services.data_monitor 重导出 DataMonitor）
  - [ ] SubTask 2.10: 创建 etf_analyzer/logger.py 兼容层（从 utils.logger 重导出 setup_logger）
  - [ ] SubTask 2.11: 创建 etf_analyzer/retry.py 兼容层（从 utils.retry 重导出 retry, rate_limiter, RateLimiter, RETRYABLE_EXCEPTIONS）
  - [ ] SubTask 2.12: 创建 etf_analyzer/secure_config.py 兼容层（从 utils.secure_config 重导出 SecureConfig, secure_config）

- [ ] Task 3: 更新 main.py 导入路径
  - [ ] SubTask 3.1: 将 main.py 中的旧导入路径更新为新路径（core/、utils/ 子包路径）

- [ ] Task 4: 更新 tests/ 下所有测试文件的导入路径
  - [ ] SubTask 4.1: 更新 test_analyzer.py（from etf_analyzer.core.analyzer import ETFAnalyzer）
  - [ ] SubTask 4.2: 更新 test_data_fetcher.py（from etf_analyzer.core.data_fetcher import ETFDataFetcher）
  - [ ] SubTask 4.3: 更新 test_data_processor.py（from etf_analyzer.core.data_processor import DataProcessor）
  - [ ] SubTask 4.4: 更新 test_data_source_manager.py（from etf_analyzer.services.data_source_manager import DataSourceManager）
  - [ ] SubTask 4.5: 更新 test_data_completion.py（from etf_analyzer.services.data_completion import DataCompletion）
  - [ ] SubTask 4.6: 更新 test_secure_config.py（from etf_analyzer.utils.secure_config import SecureConfig）
  - [ ] SubTask 4.7: 更新 test_full_validation.py（所有旧路径导入更新为新路径）

- [ ] Task 5: 运行测试验证重构正确性
  - [ ] SubTask 5.1: 执行 pytest tests/ 确认所有测试通过
  - [ ] SubTask 5.2: 验证旧路径导入兼容性（from etf_analyzer.analyzer import ETFAnalyzer 等）

# Task Dependencies
- [Task 2] depends on [Task 1]（兼容层依赖子包 __init__.py 的重新导出）
- [Task 3] depends on [Task 1]（main.py 导入依赖新路径可用）
- [Task 4] depends on [Task 1]（测试文件导入依赖新路径可用）
- [Task 5] depends on [Task 2, Task 3, Task 4]（验证需所有文件更新完成）
