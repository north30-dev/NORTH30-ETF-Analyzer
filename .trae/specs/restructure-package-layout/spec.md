# 目录结构规范化重构 Spec

## Why
当前 `etf_analyzer/` 包下所有模块文件扁平排列，随着项目规模增长，模块职责不清、难以维护。需要将扁平结构重组为 `core/`、`services/`、`utils/` 三层子包，提升代码组织性和可维护性。

## What Changes
- 将核心业务逻辑模块（analyzer, data_fetcher, data_processor, visualizer, report_generator）迁移至 `core/` 子包
- 将服务层模块（data_source_manager, data_completion, incremental_updater, data_monitor）迁移至 `services/` 子包
- 将工具类模块（logger, retry, secure_config）迁移至 `utils/` 子包
- 更新所有已移动文件的内部导入路径
- 更新 `etf_analyzer/__init__.py` 重新导出核心类
- 在旧文件位置创建兼容层（re-export），确保旧式导入路径向后兼容
- 更新 `main.py` 和所有测试文件的导入路径
- `data_sources/` 目录保持不变
- `config.py` 保持原位不变

## Impact
- Affected specs: build-etf-analyzer
- Affected code:
  - `etf_analyzer/__init__.py`（需重新导出）
  - `main.py`（需更新导入路径）
  - `tests/test_analyzer.py`、`tests/test_data_fetcher.py`、`tests/test_data_processor.py`、`tests/test_data_source_manager.py`、`tests/test_data_completion.py`、`tests/test_secure_config.py`、`tests/test_full_validation.py`（需更新导入路径）
  - 12个旧文件位置需创建兼容层

## ADDED Requirements

### Requirement: 包结构分层
系统 SHALL 将 `etf_analyzer/` 下的扁平文件结构重组为三层子包结构。

#### Scenario: 导入新路径可用
- **WHEN** 用户使用新路径导入（如 `from etf_analyzer.core.analyzer import ETFAnalyzer`）
- **THEN** 导入成功，类/函数可正常使用

#### Scenario: 旧路径向后兼容
- **WHEN** 用户使用旧路径导入（如 `from etf_analyzer.analyzer import ETFAnalyzer`）
- **THEN** 导入成功，类/函数可正常使用（通过兼容层重导出）

### Requirement: __init__.py 重新导出
`etf_analyzer/__init__.py` SHALL 重新导出核心类和函数，支持顶层快捷导入。

#### Scenario: 顶层快捷导入
- **WHEN** 用户执行 `from etf_analyzer import ETFAnalyzer`
- **THEN** 导入成功

### Requirement: 测试全部通过
重构后所有现有测试 SHALL 通过，无需修改测试逻辑（仅更新导入路径）。

#### Scenario: 运行测试套件
- **WHEN** 执行 `pytest tests/`
- **THEN** 所有测试通过，无导入错误

## MODIFIED Requirements
（无修改的需求）

## REMOVED Requirements
（无移除的需求）
