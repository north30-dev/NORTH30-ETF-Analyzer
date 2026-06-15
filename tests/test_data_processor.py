# -*- coding: utf-8 -*-
"""
DataProcessor 单元测试模块

使用纯本地数据测试 DataProcessor 的数据清洗、标准化、验证、
异常值检测、缺失值处理和数据类型转换功能，不依赖外部接口。
"""

import numpy as np
import pandas as pd
import pytest

from etf_analyzer.data_processor import DataProcessor


class TestDataProcessor:
    """DataProcessor 单元测试类。"""

    def test_init(self):
        """测试 DataProcessor 初始化是否正确设置日志。"""
        processor = DataProcessor()
        assert processor.logger is not None

    def test_clean_data_basic(self, sample_history_df):
        """测试基本数据清洗，无缺失值和异常值时数据应基本保持不变。"""
        processor = DataProcessor()
        result = processor.clean_data(sample_history_df)

        assert not result.empty
        assert len(result) > 0

    def test_clean_data_with_missing(self):
        """测试含缺失值的数据清洗，缺失值应被填充。"""
        processor = DataProcessor()
        df = pd.DataFrame(
            {
                "日期": ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
                "收盘": [3.0, np.nan, 3.2, 3.3],
                "开盘": [2.9, 3.0, np.nan, 3.2],
            }
        )
        result = processor.clean_data(df, fill_method="ffill")

        assert not result.empty
        assert result["收盘"].isnull().sum() == 0
        assert result["开盘"].isnull().sum() == 0

    def test_clean_data_with_outliers(self):
        """测试含异常值的数据清洗，异常值应被替换。"""
        processor = DataProcessor()
        # 使用足够多的正常数据点，使1000.0明显偏离3倍标准差
        normal_values = [3.0 + i * 0.01 for i in range(20)]
        values = normal_values[:5] + [1000.0] + normal_values[5:]
        df = pd.DataFrame(
            {
                "日期": pd.bdate_range(start="2024-01-02", periods=len(values)),
                "收盘": values,
            }
        )
        result = processor.clean_data(df)

        assert not result.empty
        # 1000.0 是异常值，应被替换为更合理的值
        assert result["收盘"].max() < 100.0

    def test_normalize_minmax(self):
        """测试 Min-Max 归一化，结果应在 [0, 1] 区间内。"""
        processor = DataProcessor()
        df = pd.DataFrame({"收盘": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = processor.normalize(df, method="minmax")

        assert not result.empty
        assert result["收盘"].min() == pytest.approx(0.0)
        assert result["收盘"].max() == pytest.approx(1.0)

    def test_normalize_zscore(self):
        """测试 Z-Score 标准化，结果均值应接近0，标准差接近1。"""
        processor = DataProcessor()
        df = pd.DataFrame({"收盘": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = processor.normalize(df, method="zscore")

        assert not result.empty
        assert result["收盘"].mean() == pytest.approx(0.0, abs=1e-10)
        assert result["收盘"].std() == pytest.approx(1.0, abs=1e-10)

    def test_normalize_invalid_method(self):
        """测试无效的标准化方法，应抛出 ValueError。"""
        processor = DataProcessor()
        df = pd.DataFrame({"收盘": [1.0, 2.0, 3.0]})

        with pytest.raises(ValueError, match="不支持的标准化方法"):
            processor.normalize(df, method="invalid")

    def test_validate_data_valid(self, sample_history_df):
        """测试有效数据的验证，应通过验证。"""
        processor = DataProcessor()
        passed, errors = processor.validate_data(
            sample_history_df, required_columns=["日期", "收盘"]
        )

        assert passed is True
        assert len(errors) == 0

    def test_validate_data_missing_columns(self):
        """测试缺少必需列时验证失败。"""
        processor = DataProcessor()
        df = pd.DataFrame({"开盘": [1.0, 2.0], "收盘": [1.1, 2.1]})
        passed, errors = processor.validate_data(df, required_columns=["日期", "收盘"])

        assert passed is False
        assert any("缺少必需列" in e for e in errors)

    def test_validate_data_negative_prices(self):
        """测试价格列存在负值时验证失败。"""
        processor = DataProcessor()
        df = pd.DataFrame(
            {
                "收盘": [3.0, -1.5, 3.2],
                "开盘": [2.9, 3.0, 3.1],
            }
        )
        passed, errors = processor.validate_data(df)

        assert passed is False
        assert any("负值" in e for e in errors)

    def test_validate_data_extreme_changes(self):
        """测试涨跌幅超出合理范围时验证失败。"""
        processor = DataProcessor()
        df = pd.DataFrame(
            {
                "收盘": [3.0, 3.1, 3.2],
                "涨跌幅": [1.5, 200.0, -0.5],
            }
        )
        passed, errors = processor.validate_data(df)

        assert passed is False
        assert any("超出合理范围" in e for e in errors)

    def test_detect_outliers_basic(self):
        """测试异常值检测，应正确识别偏离均值较远的值。"""
        processor = DataProcessor()
        # 使用足够多的正常数据点，使1000.0明显偏离3倍标准差
        normal_values = [3.0 + i * 0.01 for i in range(20)]
        values = normal_values[:5] + [1000.0] + normal_values[5:]
        df = pd.DataFrame({"收盘": values})
        outliers = processor.detect_outliers(df, "收盘", n_std=3)

        assert len(outliers) > 0
        # 1000.0 应被识别为异常值
        assert 5 in outliers

    def test_fill_missing_ffill(self):
        """测试前向填充缺失值。"""
        processor = DataProcessor()
        df = pd.DataFrame({"收盘": [1.0, np.nan, 3.0, 4.0]})
        result = processor.fill_missing(df, method="ffill")

        assert result["收盘"].isnull().sum() == 0
        assert result["收盘"].iloc[1] == pytest.approx(1.0)

    def test_fill_missing_mean(self):
        """测试均值填充缺失值。"""
        processor = DataProcessor()
        df = pd.DataFrame({"收盘": [1.0, np.nan, 3.0, 4.0]})
        result = processor.fill_missing(df, method="mean")

        assert result["收盘"].isnull().sum() == 0
        # 均值 = (1.0 + 3.0 + 4.0) / 3 = 2.6667
        assert result["收盘"].iloc[1] == pytest.approx(8.0 / 3, abs=0.01)

    def test_convert_dtypes(self):
        """测试数据类型转换，日期列和数值列应被正确转换。"""
        processor = DataProcessor()
        df = pd.DataFrame(
            {
                "日期": ["2024-01-02", "2024-01-03", "2024-01-04"],
                "收盘": ["3.0", "3.1", "3.2"],
                "名称": ["ETF1", "ETF2", "ETF3"],
            }
        )
        result = processor.convert_dtypes(df)

        assert not result.empty
        # 日期列应被转换为 datetime 类型
        assert pd.api.types.is_datetime64_any_dtype(result["日期"])
        # 收盘列应被转换为 float 类型
        assert pd.api.types.is_numeric_dtype(result["收盘"])
