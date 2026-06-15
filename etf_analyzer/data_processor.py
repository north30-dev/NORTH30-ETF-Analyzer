# -*- coding: utf-8 -*-
"""
ETF数据处理模块

本模块提供数据清洗、标准化、验证、异常值检测、缺失值处理和数据类型转换等功能，
用于对 ETFDataFetcher 获取的原始数据进行预处理，确保后续分析的数据质量。
"""

import numpy as np
import pandas as pd

from etf_analyzer.logger import setup_logger


class DataProcessor:
    """ETF数据处理器，提供数据清洗、标准化、验证等预处理功能。

    对 ETFDataFetcher 获取的原始 DataFrame 进行清洗、标准化、验证等操作，
    确保数据质量满足后续分析需求。

    Attributes:
        logger: 日志记录器实例。
    """

    def __init__(self):
        """初始化DataProcessor实例。

        设置日志记录器，用于记录数据处理过程中的关键操作和异常信息。
        """
        self.logger = setup_logger("data_processor")
        self.logger.info("DataProcessor 初始化完成")

    def clean_data(self, df, fill_method="ffill", drop_threshold=0.3):
        """数据清洗，依次执行缺失值处理、异常值检测与替换、格式转换。

        对原始数据进行全面清洗，包括：根据缺失率删除高缺失行、
        按指定方法填充缺失值、使用3倍标准差方法检测并替换异常值、
        确保日期列和数值列的类型正确。

        Args:
            df (pandas.DataFrame): 原始数据。
            fill_method (str): 缺失值填充方法，可选值：
                - "ffill": 前向填充（默认）
                - "bfill": 后向填充
                - "mean": 均值填充
                - "drop": 删除缺失值所在行
            drop_threshold (float): 缺失率阈值，取值范围 [0, 1]。
                当某行的缺失值比例超过此阈值时，该行将被删除。默认为 0.3。

        Returns:
            pandas.DataFrame: 清洗后的 DataFrame。如果输入为空或处理失败，
                返回空 DataFrame。

        Example:
            >>> processor = DataProcessor()
            >>> df = pd.DataFrame({"收盘": [1.0, np.nan, 3.0, 100.0]})
            >>> cleaned = processor.clean_data(df)
        """
        if df is None or df.empty:
            self.logger.warning("clean_data 接收到空 DataFrame，直接返回")
            return pd.DataFrame()

        try:
            result = df.copy()
            original_len = len(result)
            self.logger.info("开始数据清洗，原始数据行数: %d", original_len)

            # 1. 删除缺失率超过阈值的行
            threshold_count = int(len(result.columns) * drop_threshold)
            if threshold_count > 0:
                before_drop = len(result)
                result = result.dropna(thresh=len(result.columns) - threshold_count + 1)
                dropped = before_drop - len(result)
                if dropped > 0:
                    self.logger.info(
                        "删除缺失率超过 %.1f%% 的行，共删除 %d 行",
                        drop_threshold * 100, dropped,
                    )

            # 2. 填充缺失值
            result = self.fill_missing(result, method=fill_method)

            # 3. 检测并替换异常值（使用3倍标准差方法）
            numeric_cols = result.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                outlier_indices = self.detect_outliers(result, col, n_std=3)
                if outlier_indices:
                    self.logger.info(
                        "列 '%s' 检测到 %d 个异常值，使用前后均值替换",
                        col, len(outlier_indices),
                    )
                    for idx in outlier_indices:
                        prev_val = result[col].iloc[idx - 1] if idx > 0 else np.nan
                        next_val = (
                            result[col].iloc[idx + 1]
                            if idx < len(result) - 1
                            else np.nan
                        )
                        neighbors = [v for v in [prev_val, next_val] if not pd.isna(v)]
                        if neighbors:
                            result.at[result.index[idx], col] = np.mean(neighbors)

            # 4. 格式转换
            result = self.convert_dtypes(result)

            self.logger.info(
                "数据清洗完成，清洗后行数: %d，删除行数: %d",
                len(result), original_len - len(result),
            )
            return result

        except Exception as e:
            self.logger.error("数据清洗失败，异常: %s", e)
            return pd.DataFrame()

    def normalize(self, df, method="minmax", columns=None):
        """数据标准化与归一化。

        对指定列或所有数值列进行标准化/归一化处理，消除不同指标之间的
        量纲差异，便于后续的对比分析和模型训练。

        Args:
            df (pandas.DataFrame): 待处理的数据。
            method (str): 标准化方法，可选值：
                - "minmax": Min-Max 归一化，将数据缩放到 [0, 1] 区间（默认）
                - "zscore": Z-Score 标准化，将数据转换为均值为0、标准差为1的分布
            columns (list, optional): 指定需要处理的列名列表。
                如果为 None，则处理所有数值列。默认为 None。

        Returns:
            pandas.DataFrame: 标准化后的 DataFrame。如果输入为空或处理失败，
                返回空 DataFrame。

        Raises:
            ValueError: 当 method 不是 "minmax" 或 "zscore" 时抛出。

        Example:
            >>> processor = DataProcessor()
            >>> df = pd.DataFrame({"收盘": [1.0, 2.0, 3.0, 4.0, 5.0]})
            >>> normalized = processor.normalize(df, method="minmax")
            >>> print(normalized["收盘"].tolist())  # [0.0, 0.25, 0.5, 0.75, 1.0]
        """
        if df is None or df.empty:
            self.logger.warning("normalize 接收到空 DataFrame，直接返回")
            return pd.DataFrame()

        if method not in ("minmax", "zscore"):
            raise ValueError(
                f"不支持的标准化方法: '{method}'，可选值为 'minmax' 或 'zscore'"
            )

        try:
            result = df.copy()
            self.logger.info("开始数据标准化，方法: %s", method)

            # 确定需要处理的列
            if columns is None:
                target_cols = list(result.select_dtypes(include=[np.number]).columns)
            else:
                target_cols = columns

            if not target_cols:
                self.logger.warning("未找到需要标准化的数值列")
                return result

            for col in target_cols:
                if col not in result.columns:
                    self.logger.warning("列 '%s' 不存在于 DataFrame 中，跳过", col)
                    continue

                series = result[col].astype(float)
                if method == "minmax":
                    col_min = series.min()
                    col_max = series.max()
                    col_range = col_max - col_min
                    if col_range == 0:
                        self.logger.warning(
                            "列 '%s' 的最大值与最小值相同，归一化结果为0", col,
                        )
                        result[col] = 0.0
                    else:
                        result[col] = (series - col_min) / col_range
                elif method == "zscore":
                    col_mean = series.mean()
                    col_std = series.std()
                    if col_std == 0:
                        self.logger.warning(
                            "列 '%s' 的标准差为0，标准化结果为0", col,
                        )
                        result[col] = 0.0
                    else:
                        result[col] = (series - col_mean) / col_std

            self.logger.info("数据标准化完成，处理列数: %d", len(target_cols))
            return result

        except Exception as e:
            self.logger.error("数据标准化失败，异常: %s", e)
            return pd.DataFrame()

    def validate_data(self, df, required_columns=None):
        """数据验证，检查数据完整性、类型和合理性。

        对 DataFrame 进行多维度验证，包括必需列是否存在、数值列类型是否正确、
        价格类列是否存在负值、涨跌幅是否在合理范围内等。

        Args:
            df (pandas.DataFrame): 待验证的数据。
            required_columns (list, optional): 必需列名列表。
                如果提供，将检查这些列是否存在于 DataFrame 中。默认为 None。

        Returns:
            tuple: (bool, list) 元组：
                - bool: 是否通过全部验证，True 表示通过，False 表示存在错误
                - list: 错误信息列表，包含所有未通过验证项的详细描述

        Example:
            >>> processor = DataProcessor()
            >>> df = pd.DataFrame({"收盘": [1.0, -2.0], "涨跌幅": [0.01, 5.0]})
            >>> passed, errors = processor.validate_data(df, required_columns=["收盘"])
            >>> print(passed)  # False
            >>> print(errors)  # 包含价格负值和涨跌幅异常的错误信息
        """
        errors = []

        if df is None or df.empty:
            errors.append("DataFrame 为空或 None")
            self.logger.warning("数据验证失败: DataFrame 为空")
            return False, errors

        try:
            self.logger.info("开始数据验证，数据行数: %d，列数: %d", len(df), len(df.columns))

            # 1. 验证完整性：检查必需列是否存在
            if required_columns:
                missing_cols = [col for col in required_columns if col not in df.columns]
                if missing_cols:
                    errors.append(f"缺少必需列: {missing_cols}")
                    self.logger.warning("数据验证: 缺少必需列 %s", missing_cols)

            # 2. 验证类型：检查数值列是否为数值类型
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            # 常见的数值列名称模式
            numeric_name_patterns = [
                "价", "幅", "量", "额", "率", "收益", "波动", "夏普",
                "最大回撤", "均值", "标准差",
            ]
            for col in df.columns:
                # 跳过已经是数值类型的列
                if col in numeric_cols:
                    continue
                # 检查列名是否暗示应为数值类型
                if any(pattern in col for pattern in numeric_name_patterns):
                    try:
                        df[col].astype(float)
                    except (ValueError, TypeError):
                        errors.append(f"列 '{col}' 应为数值类型，但包含非数值数据")
                        self.logger.warning("数据验证: 列 '%s' 类型异常", col)

            # 3. 验证范围：检查价格类列是否有负值
            price_keywords = ["价", "收盘", "开盘", "最高", "最低", "昨收"]
            for col in numeric_cols:
                if any(keyword in col for keyword in price_keywords):
                    if (df[col] < 0).any():
                        neg_count = (df[col] < 0).sum()
                        errors.append(
                            f"价格列 '{col}' 存在 {neg_count} 个负值"
                        )
                        self.logger.warning(
                            "数据验证: 价格列 '%s' 存在 %d 个负值", col, neg_count,
                        )

            # 4. 验证范围：检查涨跌幅是否在合理范围（-100% ~ 100%）
            change_keywords = ["涨跌幅", "涨跌", "变化率", "变动"]
            for col in numeric_cols:
                if any(keyword in col for keyword in change_keywords):
                    if (df[col].abs() > 100).any():
                        extreme_count = (df[col].abs() > 100).sum()
                        errors.append(
                            f"涨跌幅列 '{col}' 存在 {extreme_count} 个超出合理范围"
                            f"（-100%~100%）的值"
                        )
                        self.logger.warning(
                            "数据验证: 涨跌幅列 '%s' 存在 %d 个异常值",
                            col, extreme_count,
                        )

            passed = len(errors) == 0
            if passed:
                self.logger.info("数据验证通过")
            else:
                self.logger.warning("数据验证未通过，共 %d 个错误", len(errors))

            return passed, errors

        except Exception as e:
            errors.append(f"数据验证过程发生异常: {e}")
            self.logger.error("数据验证异常: %s", e)
            return False, errors

    def detect_outliers(self, df, column, n_std=3):
        """使用标准差方法检测异常值。

        计算指定列的均值和标准差，将偏离均值超过 n_std 倍标准差的数据点
        标记为异常值。

        Args:
            df (pandas.DataFrame): 待检测的数据。
            column (str): 需要检测异常值的列名。
            n_std (int or float): 标准差倍数阈值，超过此范围的值将被视为异常值。
                默认为 3，即3倍标准差。

        Returns:
            list: 异常值在 DataFrame 中的位置索引列表（基于整数位置）。
                如果列不存在或数据为空，返回空列表。

        Example:
            >>> processor = DataProcessor()
            >>> df = pd.DataFrame({"收盘": [1.0, 1.1, 1.2, 100.0, 1.3]})
            >>> outliers = processor.detect_outliers(df, "收盘", n_std=3)
            >>> print(outliers)  # [3]（100.0 为异常值）
        """
        if df is None or df.empty:
            self.logger.warning("detect_outliers 接收到空 DataFrame，返回空列表")
            return []

        if column not in df.columns:
            self.logger.warning("列 '%s' 不存在于 DataFrame 中", column)
            return []

        try:
            series = pd.to_numeric(df[column], errors="coerce")
            series = series.dropna()

            if series.empty:
                self.logger.warning("列 '%s' 无有效数值数据", column)
                return []

            mean = series.mean()
            std = series.std()

            if std == 0:
                self.logger.info("列 '%s' 标准差为0，无异常值", column)
                return []

            lower_bound = mean - n_std * std
            upper_bound = mean + n_std * std

            # 返回基于整数位置的索引
            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_positions = [
                series.index.get_loc(idx) for idx in series[outlier_mask].index
            ]

            if outlier_positions:
                self.logger.info(
                    "列 '%s' 检测到 %d 个异常值（%d倍标准差），"
                    "范围: [%.4f, %.4f]，均值: %.4f，标准差: %.4f",
                    column, len(outlier_positions), n_std,
                    lower_bound, upper_bound, mean, std,
                )

            return outlier_positions

        except Exception as e:
            self.logger.error("异常值检测失败，列: '%s'，异常: %s", column, e)
            return []

    def fill_missing(self, df, method="ffill"):
        """缺失值处理。

        根据指定的方法对 DataFrame 中的缺失值进行填充或删除处理。

        Args:
            df (pandas.DataFrame): 待处理的数据。
            method (str): 填充方法，可选值：
                - "ffill": 前向填充，用前一个有效值填充（默认）
                - "bfill": 后向填充，用后一个有效值填充
                - "mean": 均值填充，用列均值填充
                - "interpolate": 线性插值填充
                - "drop": 删除包含缺失值的行

        Returns:
            pandas.DataFrame: 处理缺失值后的 DataFrame。如果输入为空或处理失败，
                返回空 DataFrame。

        Example:
            >>> processor = DataProcessor()
            >>> df = pd.DataFrame({"收盘": [1.0, np.nan, 3.0]})
            >>> filled = processor.fill_missing(df, method="ffill")
            >>> print(filled["收盘"].tolist())  # [1.0, 1.0, 3.0]
        """
        if df is None or df.empty:
            self.logger.warning("fill_missing 接收到空 DataFrame，直接返回")
            return pd.DataFrame()

        try:
            result = df.copy()
            missing_before = result.isnull().sum().sum()
            self.logger.info(
                "开始缺失值处理，方法: %s，缺失值总数: %d", method, missing_before,
            )

            if missing_before == 0:
                self.logger.info("数据无缺失值，跳过处理")
                return result

            valid_methods = ("ffill", "bfill", "mean", "interpolate", "drop")
            if method not in valid_methods:
                self.logger.warning(
                    "不支持的填充方法: '%s'，使用默认方法 'ffill'", method,
                )
                method = "ffill"

            if method == "ffill":
                result = result.ffill()
                # 首行可能仍为 NaN，用 bfill 补充
                result = result.bfill()
            elif method == "bfill":
                result = result.bfill()
                # 末行可能仍为 NaN，用 ffill 补充
                result = result.ffill()
            elif method == "mean":
                numeric_cols = result.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    col_mean = result[col].mean()
                    result[col] = result[col].fillna(col_mean)
                # 非数值列用 ffill 兜底
                result = result.ffill().bfill()
            elif method == "interpolate":
                numeric_cols = result.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    result[col] = result[col].interpolate(method="linear")
                # 首尾可能仍有 NaN
                result = result.ffill().bfill()
            elif method == "drop":
                result = result.dropna()

            missing_after = result.isnull().sum().sum()
            self.logger.info(
                "缺失值处理完成，处理前: %d，处理后: %d", missing_before, missing_after,
            )
            return result

        except Exception as e:
            self.logger.error("缺失值处理失败，异常: %s", e)
            return pd.DataFrame()

    def convert_dtypes(self, df):
        """数据类型转换。

        自动检测 DataFrame 中的日期列和数值列，并将其转换为正确的数据类型。
        日期列转换为 datetime 类型，数值列转换为 float 类型。

        Args:
            df (pandas.DataFrame): 待转换的数据。

        Returns:
            pandas.DataFrame: 类型转换后的 DataFrame。如果输入为空或处理失败，
                返回空 DataFrame。

        Example:
            >>> processor = DataProcessor()
            >>> df = pd.DataFrame({"日期": ["2024-01-01", "2024-01-02"], "收盘": ["1.0", "2.0"]})
            >>> converted = processor.convert_dtypes(df)
            >>> print(converted.dtypes)  # 日期: datetime64[ns], 收盘: float64
        """
        if df is None or df.empty:
            self.logger.warning("convert_dtypes 接收到空 DataFrame，直接返回")
            return pd.DataFrame()

        try:
            result = df.copy()
            self.logger.info("开始数据类型转换，列数: %d", len(result.columns))

            # 日期列名称关键词
            date_keywords = ["日期", "时间", "date", "time", "交易日期"]

            for col in result.columns:
                # 尝试转换日期列
                if any(keyword in col.lower() for keyword in date_keywords):
                    try:
                        result[col] = pd.to_datetime(result[col], errors="coerce")
                        self.logger.info("列 '%s' 转换为 datetime 类型", col)
                        continue
                    except Exception:
                        pass

                # 尝试转换数值列（兼容 object 和 string dtype）
                if result[col].dtype == object or pd.api.types.is_string_dtype(result[col]):
                    try:
                        converted = pd.to_numeric(result[col], errors="coerce")
                        # 如果转换后非空值比例较高，则认为该列应为数值类型
                        non_null_ratio = converted.notna().sum() / len(converted)
                        original_non_null = result[col].notna().sum() / len(result[col])
                        if non_null_ratio >= original_non_null * 0.9:
                            result[col] = converted
                            self.logger.info("列 '%s' 转换为 float 类型", col)
                    except Exception:
                        self.logger.debug("列 '%s' 无法转换为数值类型，保持原样", col)

            self.logger.info("数据类型转换完成")
            return result

        except Exception as e:
            self.logger.error("数据类型转换失败，异常: %s", e)
            return pd.DataFrame()
