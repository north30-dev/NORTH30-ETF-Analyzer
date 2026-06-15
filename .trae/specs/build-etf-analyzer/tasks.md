# Tasks

- [ ] Task 1: 项目基础架构搭建
  - [ ] SubTask 1.1: 创建 requirements.txt，声明所有依赖（akshare, pandas, numpy, matplotlib, reportlab 等）
  - [ ] SubTask 1.2: 创建 config.py，定义全局配置（缓存路径、默认参数、行业分类映射等）
  - [ ] SubTask 1.3: 创建 logger.py，实现统一日志记录模块
  - [ ] SubTask 1.4: 创建项目目录结构（etf_analyzer/ 包目录及各模块文件）

- [ ] Task 2: 数据获取模块开发（data_fetcher.py）
  - [ ] SubTask 2.1: 实现实时 ETF 行情数据获取（最新价格、涨跌幅、成交量等）
  - [ ] SubTask 2.2: 实现历史 ETF 数据获取，支持自定义时间范围
  - [ ] SubTask 2.3: 实现数据缓存机制（基于文件缓存，支持过期时间配置）
  - [ ] SubTask 2.4: 实现 ETF 列表查询与搜索功能

- [ ] Task 3: 数据处理模块开发（data_processor.py）
  - [ ] SubTask 3.1: 实现数据清洗功能（缺失值处理、异常值检测与修正、格式转换）
  - [ ] SubTask 3.2: 实现数据标准化（Z-Score）与归一化（Min-Max）处理
  - [ ] SubTask 3.3: 实现数据验证机制（完整性、类型、范围检查）

- [ ] Task 4: 核心分析模块开发（analyzer.py）
  - [ ] SubTask 4.1: 实现净值走势分析（复权处理、累计收益率、年化收益率、趋势判断）
  - [ ] SubTask 4.2: 实现成分股构成分析（前十大权重股、持仓集中度）
  - [ ] SubTask 4.3: 实现行业分布统计（申万/中信行业分类映射与持仓分布统计）
  - [ ] SubTask 4.4: 实现风险指标计算（波动率、最大回撤、夏普比率、信息比率）
  - [ ] SubTask 4.5: 实现绩效分析（基准对比、超额收益、跟踪误差）

- [ ] Task 5: 可视化模块开发（visualizer.py）
  - [ ] SubTask 5.1: 实现 K 线图绘制（含成交量副图）
  - [ ] SubTask 5.2: 实现净值走势图绘制（含基准对比）
  - [ ] SubTask 5.3: 实现行业分布饼图绘制
  - [ ] SubTask 5.4: 实现成分股权重柱状图绘制
  - [ ] SubTask 5.5: 实现图表自定义功能（时间范围选择、指标切换）

- [ ] Task 6: 报告生成模块开发（report_generator.py）
  - [ ] SubTask 6.1: 实现 PDF 报告基础框架（标题、目录、页眉页脚）
  - [ ] SubTask 6.2: 实现关键指标概览部分
  - [ ] SubTask 6.3: 实现图表嵌入展示
  - [ ] SubTask 6.4: 实现文字分析部分
  - [ ] SubTask 6.5: 实现自定义报告模块选择功能

- [ ] Task 7: 命令行交互入口开发（main.py）
  - [ ] SubTask 7.1: 设计并实现主菜单导航
  - [ ] SubTask 7.2: 实现各功能模块子菜单与操作流程
  - [ ] SubTask 7.3: 集成所有模块，实现完整交互流程

- [x] Task 8: 单元测试开发（tests/）
  - [x] SubTask 8.1: 为数据获取模块编写单元测试
  - [x] SubTask 8.2: 为数据处理模块编写单元测试
  - [x] SubTask 8.3: 为核心分析模块编写单元测试
  - [x] SubTask 8.4: 提供测试数据和测试用例

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 4]
- [Task 6] depends on [Task 4, Task 5]
- [Task 7] depends on [Task 2, Task 3, Task 4, Task 5, Task 6]
- [Task 8] depends on [Task 2, Task 3, Task 4]
