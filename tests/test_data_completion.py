# -*- coding: utf-8 -*-
"""
智能数据补全模块单元测试

使用 mock 和构造测试数据，测试 DataCompletion 的缺失日期填充、
交叉验证和质量评分功能。
"""

import numpy as np
import pandas as pd
import pytest

from etf_analyzer.services.data_completion import DataCompletion


# ============================================================
# 测试缺失日期填充
# ============================================================


class TestFillMissingDates:
    """缺失日期填充相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.completion = DataCompletion()

    def test_interpolate_fill(self):
        """测试线性插值填充缺失日期。"""
        # 构造有缺失日期的数据：1月2日、1月4日有数据，1月3日缺失
        df = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02", "2024-01-04"]),
            "收盘": [3.0, 5.0],
            "开盘": [2.9, 4.9],
        })

        result = self.completion.fill_missing_dates(df, method="interpolate")

        # 应包含3行（1月2日、3日、4日）
        assert len(result) == 3
        # 1月3日的收盘价应为线性插值 (3.0 + 5.0) / 2 = 4.0
        filled_row = result[result["日期"] == pd.Timestamp("2024-01-03")]
        assert not filled_row.empty
        assert abs(filled_row.iloc[0]["收盘"] - 4.0) < 0.01

    def test_neighbor_mean_fill(self):
        """测试前后均值填充缺失日期。"""
        df = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02", "2024-01-04"]),
            "收盘": [3.0, 5.0],
            "开盘": [2.9, 4.9],
        })

        result = self.completion.fill_missing_dates(df, method="neighbor_mean")

        # 应包含3行
        assert len(result) == 3
        # 1月3日的收盘价应为前后均值 (3.0 + 5.0) / 2 = 4.0
        filled_row = result[result["日期"] == pd.Timestamp("2024-01-03")]
        assert not filled_row.empty
        assert abs(filled_row.iloc[0]["收盘"] - 4.0) < 0.01

    def test_filled_data_marked_as_completion(self):
        """测试填充的数据行标记为'补全'。"""
        df = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02", "2024-01-04"]),
            "收盘": [3.0, 5.0],
        })

        result = self.completion.fill_missing_dates(df, method="interpolate")

        # 原始数据标记为"原始"
        original_rows = result[result["日期"] == pd.Timestamp("2024-01-02")]
        assert original_rows.iloc[0]["_data_source"] == "原始"

        # 填充数据标记为"补全"
        filled_rows = result[result["日期"] == pd.Timestamp("2024-01-03")]
        assert filled_rows.iloc[0]["_data_source"] == "补全"

    def test_no_missing_dates(self):
        """测试无缺失日期时直接标记为'原始'。"""
        df = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "收盘": [3.0, 4.0, 5.0],
        })

        result = self.completion.fill_missing_dates(df)

        assert len(result) == 3
        assert all(result["_data_source"] == "原始")

    def test_empty_dataframe_returns_empty(self):
        """测试空 DataFrame 返回空 DataFrame。"""
        result = self.completion.fill_missing_dates(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_none_returns_empty(self):
        """测试 None 输入返回空 DataFrame。"""
        result = self.completion.fill_missing_dates(None)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_missing_date_column_returns_original(self):
        """测试缺少日期列时返回原始数据。"""
        df = pd.DataFrame({"收盘": [3.0, 4.0, 5.0]})
        result = self.completion.fill_missing_dates(df)
        assert len(result) == 3


# ============================================================
# 测试交叉验证
# ============================================================


class TestCrossValidate:
    """交叉验证相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.completion = DataCompletion()

    def test_multi_source_merge(self):
        """测试多源数据合并。"""
        df1 = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "收盘": [3.0, 4.0],
            "开盘": [2.9, 3.9],
        })
        df2 = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "收盘": [3.01, 4.01],
            "开盘": [2.91, 3.91],
        })

        merged_df, conflict_info = self.completion.cross_validate({
            "akshare": df1,
            "tushare": df2,
        })

        # 应有2行合并数据
        assert len(merged_df) == 2
        # 数据差异很小，不应有冲突
        assert len(conflict_info) == 0
        # _data_source 应标记为"交叉验证"
        assert all(merged_df["_data_source"] == "交叉验证")

    def test_conflict_marked_when_diff_exceeds_threshold(self):
        """测试差异超阈值时标记为'数据冲突'。"""
        df1 = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02"]),
            "收盘": [3.0],
        })
        df2 = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02"]),
            "收盘": [5.0],  # 差异超过 1% 阈值
        })

        merged_df, conflict_info = self.completion.cross_validate(
            {"akshare": df1, "tushare": df2},
            threshold=1.0,  # 1% 阈值
        )

        # 应有冲突记录
        assert len(conflict_info) > 0
        # _data_source 应标记为"数据冲突"
        assert merged_df.iloc[0]["_data_source"] == "数据冲突"

    def test_median_value_used_for_merge(self):
        """测试合并时取中位数。"""
        df1 = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02"]),
            "收盘": [3.0],
        })
        df2 = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02"]),
            "收盘": [5.0],
        })

        merged_df, _ = self.completion.cross_validate(
            {"akshare": df1, "tushare": df2},
            threshold=100.0,  # 设置高阈值避免冲突标记
        )

        # 中位数应为 (3.0 + 5.0) / 2 = 4.0
        assert abs(merged_df.iloc[0]["收盘"] - 4.0) < 0.01

    def test_single_source_no_cross_validation(self):
        """测试仅一个数据源时无需交叉验证。"""
        df = pd.DataFrame({
            "日期": pd.to_datetime(["2024-01-02"]),
            "收盘": [3.0],
        })

        merged_df, conflict_info = self.completion.cross_validate({"akshare": df})

        assert len(merged_df) == 1
        assert len(conflict_info) == 0
        assert merged_df.iloc[0]["_data_source"] == "交叉验证"

    def test_empty_data_dict_returns_empty(self):
        """测试空数据字典返回空结果。"""
        merged_df, conflict_info = self.completion.cross_validate({})
        assert isinstance(merged_df, pd.DataFrame)
        assert merged_df.empty
        assert conflict_info == []


# ============================================================
# 测试质量评分
# ============================================================


class TestQualityScore:
    """质量评分相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.completion = DataCompletion()

    def test_complete_data_score_near_100(self):
        """测试完整数据评分接近100。"""
        # 无缺失值的完整数据
        df = pd.DataFrame({
            "日期": pd.date_range("2024-01-02", periods=30),
            "收盘": np.random.uniform(3.0, 5.0, 30),
            "开盘": np.random.uniform(3.0, 5.0, 30),
        })

        score = self.completion.calculate_quality_score(df, source_count=3, conflict_count=0)

        # 完整数据 + 3个来源 + 无冲突，评分应接近100
        assert score >= 90.0

    def test_missing_data_score_lower(self):
        """测试缺失数据评分较低。"""
        # 有大量缺失值的数据
        df = pd.DataFrame({
            "日期": pd.date_range("2024-01-02", periods=10),
            "收盘": [3.0, np.nan, 4.0, np.nan, 5.0, np.nan, 3.5, np.nan, 4.5, np.nan],
            "开盘": [2.9, 3.9, np.nan, 4.9, np.nan, 3.4, np.nan, 4.4, np.nan, 2.8],
        })

        score = self.completion.calculate_quality_score(df, source_count=1, conflict_count=0)

        # 缺失数据 + 单来源，评分应较低
        assert score < 80.0

    def test_multi_source_score_higher_than_single(self):
        """测试多源数据评分高于单源。"""
        df = pd.DataFrame({
            "日期": pd.date_range("2024-01-02", periods=10),
            "收盘": np.random.uniform(3.0, 5.0, 10),
        })

        score_single = self.completion.calculate_quality_score(df, source_count=1, conflict_count=0)
        score_multi = self.completion.calculate_quality_score(df, source_count=3, conflict_count=0)

        # 多源评分应高于单源
        assert score_multi > score_single

    def test_empty_dataframe_returns_zero(self):
        """测试空 DataFrame 返回 0.0。"""
        score = self.completion.calculate_quality_score(pd.DataFrame())
        assert score == 0.0

    def test_none_returns_zero(self):
        """测试 None 输入返回 0.0。"""
        score = self.completion.calculate_quality_score(None)
        assert score == 0.0

    def test_conflict_reduces_score(self):
        """测试冲突数降低评分。"""
        df = pd.DataFrame({
            "日期": pd.date_range("2024-01-02", periods=10),
            "收盘": np.random.uniform(3.0, 5.0, 10),
        })

        score_no_conflict = self.completion.calculate_quality_score(df, source_count=2, conflict_count=0)
        score_with_conflict = self.completion.calculate_quality_score(df, source_count=2, conflict_count=5)

        # 有冲突的评分应低于无冲突
        assert score_with_conflict < score_no_conflict


# ============================================================
# 测试缺失值填充
# ============================================================


class TestFillMissingValues:
    """缺失值填充相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.completion = DataCompletion()

    def test_interpolate_fill_missing_values(self):
        """测试线性插值填充缺失值。"""
        df = pd.DataFrame({
            "收盘": [3.0, np.nan, 5.0],
            "开盘": [2.9, np.nan, 4.9],
        })

        result = self.completion.fill_missing_values(df, method="interpolate")

        # 缺失值应被填充
        assert not result["收盘"].isna().any()
        # 中间值应接近线性插值
        assert abs(result.iloc[1]["收盘"] - 4.0) < 0.01

    def test_filled_rows_marked_as_completion(self):
        """测试被填充的行标记为'补全'。"""
        df = pd.DataFrame({
            "收盘": [3.0, np.nan, 5.0],
        })

        result = self.completion.fill_missing_values(df)

        # 原始行标记为"原始"
        assert result.iloc[0]["_data_source"] == "原始"
        assert result.iloc[2]["_data_source"] == "原始"
        # 填充行标记为"补全"
        assert result.iloc[1]["_data_source"] == "补全"

    def test_no_missing_values(self):
        """测试无缺失值时跳过处理。"""
        df = pd.DataFrame({
            "收盘": [3.0, 4.0, 5.0],
        })

        result = self.completion.fill_missing_values(df)

        assert len(result) == 3
        assert "_data_source" in result.columns
        assert all(result["_data_source"] == "原始")

    def test_empty_dataframe_returns_empty(self):
        """测试空 DataFrame 返回空 DataFrame。"""
        result = self.completion.fill_missing_values(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ============================================================
# 测试质量报告生成
# ============================================================


class TestGenerateQualityReport:
    """质量报告生成相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.completion = DataCompletion()

    def test_report_contains_required_fields(self):
        """测试报告包含所有必需字段。"""
        df = pd.DataFrame({
            "日期": pd.date_range("2024-01-02", periods=10),
            "收盘": np.random.uniform(3.0, 5.0, 10),
        })

        report = self.completion.generate_quality_report(df, source_count=2)

        required_fields = ["score", "total_rows", "complete_rows", "missing_ratio",
                           "source_count", "conflict_count", "filled_count", "details"]
        for field in required_fields:
            assert field in report

    def test_report_with_filled_data(self):
        """测试包含补全数据的报告。"""
        df = pd.DataFrame({
            "收盘": [3.0, 4.0, 5.0],
            "_data_source": ["原始", "补全", "原始"],
        })

        report = self.completion.generate_quality_report(df)

        assert report["filled_count"] == 1

    def test_empty_dataframe_report(self):
        """测试空 DataFrame 的报告。"""
        report = self.completion.generate_quality_report(pd.DataFrame())

        assert report["score"] == 0.0
        assert report["total_rows"] == 0
        assert report["missing_ratio"] == 1.0
