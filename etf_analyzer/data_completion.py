# -*- coding: utf-8 -*-
"""
ETF数据智能补全模块

本模块提供缺失数据智能填充、多源数据交叉验证和数据质量评分功能，
用于提升 ETF 数据的完整性和可靠性。
"""

import numpy as np
import pandas as pd

from etf_analyzer import config
from etf_analyzer.logger import setup_logger


class DataCompletion:
    """ETF数据智能补全器，提供缺失数据填充、交叉验证和质量评分功能。

    对 ETF 数据进行缺失日期填充、缺失值补全、多源数据交叉验证，
    并生成数据质量评分报告，确保数据完整性和可靠性。

    Attributes:
        logger: 日志记录器实例。
    """

    def __init__(self):
        """初始化DataCompletion实例。

        设置日志记录器，用于记录数据补全过程中的关键操作和异常信息。
        """
        self.logger = setup_logger("data_completion")
        self.logger.info("DataCompletion 初始化完成")

    def fill_missing_dates(self, df, date_col="日期", method="interpolate"):
        """缺失日期数据填充。

        检测 DataFrame 中按日期排列的缺失交易日数据，并根据指定方法
        进行填充。填充的数据行通过 _data_source 列标记为"补全"，
        原始数据行标记为"原始"。

        Args:
            df (pandas.DataFrame): 待处理的 DataFrame，须包含日期列。
            date_col (str): 日期列的列名，默认为 "日期"。
            method (str): 填充方法，可选值：
                - "interpolate": 线性插值（默认）
                - "neighbor_mean": 前后均值法

        Returns:
            pandas.DataFrame: 填充后的 DataFrame，包含 _data_source 列。
                如果输入为空或处理失败，返回空 DataFrame。
        """
        if df is None or df.empty:
            self.logger.warning("fill_missing_dates 接收到空 DataFrame，直接返回")
            return pd.DataFrame()

        if date_col not in df.columns:
            self.logger.warning(
                "日期列 '%s' 不存在于 DataFrame 中，无法填充缺失日期", date_col,
            )
            return df.copy()

        try:
            result = df.copy()
            original_len = len(result)

            # 确保日期列为 datetime 类型
            result[date_col] = pd.to_datetime(result[date_col], errors="coerce")

            # 按日期排序
            result = result.sort_values(date_col).reset_index(drop=True)

            # 生成完整的日期范围（按日）
            date_min = result[date_col].min()
            date_max = result[date_col].max()
            full_dates = pd.date_range(start=date_min, end=date_max, freq="D")

            # 找出缺失的日期
            existing_dates = set(result[date_col].dt.normalize())
            missing_dates = [d for d in full_dates if d.normalize() not in existing_dates]

            if not missing_dates:
                self.logger.info("未检测到缺失日期，无需填充")
                result["_data_source"] = "原始"
                return result

            self.logger.info(
                "检测到 %d 个缺失日期，使用 '%s' 方法填充",
                len(missing_dates), method,
            )

            # 标记原始数据
            result["_data_source"] = "原始"

            # 将日期设为索引以便 reindex
            result = result.set_index(date_col)

            # 创建包含所有日期的完整索引
            full_index = pd.DatetimeIndex(full_dates)

            # 对数值列进行 reindex，插入缺失日期行
            result = result.reindex(full_index)

            # 填充缺失日期的数值
            numeric_cols = result.select_dtypes(include=[np.number]).columns.tolist()
            # 排除 _data_source 列（如果被误识别为数值）
            if "_data_source" in numeric_cols:
                numeric_cols.remove("_data_source")

            if method == "interpolate":
                # 线性插值
                for col in numeric_cols:
                    result[col] = result[col].interpolate(method="linear")
                # 首尾可能仍有 NaN，用 ffill/bfill 补充
                result[numeric_cols] = result[numeric_cols].ffill().bfill()
            elif method == "neighbor_mean":
                # 前后均值法：对每个缺失位置取前后非缺失值的均值
                for col in numeric_cols:
                    series = result[col].copy()
                    na_mask = series.isna()
                    for idx in series[na_mask].index:
                        # 找前一个非缺失值
                        prev_vals = series.loc[:idx].dropna()
                        prev_val = prev_vals.iloc[-1] if len(prev_vals) > 0 else np.nan
                        # 找后一个非缺失值
                        next_vals = series.loc[idx:].dropna()
                        next_val = next_vals.iloc[0] if len(next_vals) > 0 else np.nan

                        neighbors = [v for v in [prev_val, next_val] if not pd.isna(v)]
                        if neighbors:
                            series.at[idx] = np.mean(neighbors)
                    result[col] = series
                # 首尾可能仍有 NaN，用 ffill/bfill 补充
                result[numeric_cols] = result[numeric_cols].ffill().bfill()
            else:
                self.logger.warning(
                    "不支持的填充方法: '%s'，使用默认方法 'interpolate'", method,
                )
                for col in numeric_cols:
                    result[col] = result[col].interpolate(method="linear")
                result[numeric_cols] = result[numeric_cols].ffill().bfill()

            # 标记数据来源
            result["_data_source"] = result["_data_source"].fillna("补全")

            # 恢复日期列
            result.index.name = date_col
            result = result.reset_index()

            filled_count = len(result) - original_len
            self.logger.info(
                "缺失日期填充完成，原始行数: %d，填充后行数: %d，补全行数: %d",
                original_len, len(result), filled_count,
            )
            return result

        except Exception as e:
            self.logger.error("缺失日期填充失败，异常: %s", e)
            return pd.DataFrame()

    def fill_missing_values(self, df, columns=None, method="interpolate"):
        """缺失值填充。

        对 DataFrame 中的 NaN 值进行填充，填充的值通过 _data_source 列
        标记来源为"补全"。

        Args:
            df (pandas.DataFrame): 待处理的 DataFrame。
            columns (list, optional): 需要填充的列名列表。
                如果为 None，则处理所有数值列。默认为 None。
            method (str): 填充方法，可选值：
                - "interpolate": 线性插值（默认）
                - "ffill": 前向填充
                - "bfill": 后向填充
                - "mean": 均值填充

        Returns:
            pandas.DataFrame: 填充后的 DataFrame，包含 _data_source 列。
                如果输入为空或处理失败，返回空 DataFrame。
        """
        if df is None or df.empty:
            self.logger.warning("fill_missing_values 接收到空 DataFrame，直接返回")
            return pd.DataFrame()

        try:
            result = df.copy()

            # 确定需要处理的列
            if columns is None:
                target_cols = result.select_dtypes(include=[np.number]).columns.tolist()
            else:
                target_cols = [c for c in columns if c in result.columns]

            if not target_cols:
                self.logger.warning("未找到需要填充的数值列")
                return result

            # 记录哪些行原本有缺失值
            has_missing = result[target_cols].isna().any(axis=1)

            missing_before = result[target_cols].isna().sum().sum()
            self.logger.info(
                "开始缺失值填充，方法: '%s'，目标列: %s，缺失值总数: %d",
                method, target_cols, missing_before,
            )

            if missing_before == 0:
                self.logger.info("数据无缺失值，跳过处理")
                if "_data_source" not in result.columns:
                    result["_data_source"] = "原始"
                return result

            valid_methods = ("interpolate", "ffill", "bfill", "mean")
            if method not in valid_methods:
                self.logger.warning(
                    "不支持的填充方法: '%s'，使用默认方法 'interpolate'", method,
                )
                method = "interpolate"

            if method == "interpolate":
                for col in target_cols:
                    result[col] = result[col].interpolate(method="linear")
                # 首尾可能仍有 NaN
                result[target_cols] = result[target_cols].ffill().bfill()
            elif method == "ffill":
                result[target_cols] = result[target_cols].ffill()
                result[target_cols] = result[target_cols].bfill()
            elif method == "bfill":
                result[target_cols] = result[target_cols].bfill()
                result[target_cols] = result[target_cols].ffill()
            elif method == "mean":
                for col in target_cols:
                    col_mean = result[col].mean()
                    result[col] = result[col].fillna(col_mean)
                # 非数值列可能仍有 NaN
                result[target_cols] = result[target_cols].ffill().bfill()

            # 设置 _data_source 列
            if "_data_source" not in result.columns:
                result["_data_source"] = "原始"
            # 被填充的行标记为"补全"
            result.loc[has_missing, "_data_source"] = "补全"

            missing_after = result[target_cols].isna().sum().sum()
            self.logger.info(
                "缺失值填充完成，处理前: %d，处理后: %d", missing_before, missing_after,
            )
            return result

        except Exception as e:
            self.logger.error("缺失值填充失败，异常: %s", e)
            return pd.DataFrame()

    def cross_validate(self, data_dict, threshold=None):
        """多源数据交叉验证。

        对齐各数据源的日期索引，对每个交易日的数值列进行对比，
        差异超过阈值的标记为"数据冲突"，取各数据源的中位数作为最终值。

        Args:
            data_dict (dict): 字典，键为数据源名称，值为 DataFrame。
                各数据源返回的同一 ETF 同一时间范围的数据。
            threshold (float, optional): 差异阈值百分比。
                默认从 config.CROSS_VALIDATION_THRESHOLD 读取（1.0%）。

        Returns:
            tuple: (merged_df, conflict_info) 元组：
                - merged_df: 合并后的 DataFrame，包含 _data_source 列
                  （值为 "交叉验证" 或 "数据冲突"）
                - conflict_info: 冲突信息列表，每项为 dict，包含 date、column、
                  sources（各数据源的值）、diff_pct（差异百分比）

                如果输入为空或处理失败，返回 (空 DataFrame, 空列表)。
        """
        if not data_dict:
            self.logger.warning("cross_validate 接收到空数据字典，直接返回")
            return pd.DataFrame(), []

        # 过滤空 DataFrame
        valid_sources = {
            name: df for name, df in data_dict.items()
            if df is not None and not df.empty
        }

        if not valid_sources:
            self.logger.warning("所有数据源的 DataFrame 均为空，直接返回")
            return pd.DataFrame(), []

        if len(valid_sources) == 1:
            self.logger.info("仅有一个有效数据源，无需交叉验证")
            source_name, source_df = list(valid_sources.items())[0]
            result = source_df.copy()
            result["_data_source"] = "交叉验证"
            return result, []

        try:
            if threshold is None:
                threshold = config.CROSS_VALIDATION_THRESHOLD

            self.logger.info(
                "开始多源数据交叉验证，数据源: %s，差异阈值: %.2f%%",
                list(valid_sources.keys()), threshold,
            )

            conflict_info = []

            # 统一日期列名并设为索引
            standardized = {}
            for name, df in valid_sources.items():
                temp = df.copy()
                # 查找日期列
                date_col = None
                for col in temp.columns:
                    if any(kw in col for kw in ["日期", "时间", "date", "time"]):
                        date_col = col
                        break

                if date_col is None:
                    self.logger.warning(
                        "数据源 '%s' 未找到日期列，跳过", name,
                    )
                    continue

                temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
                temp = temp.set_index(date_col)
                temp.index.name = "日期"
                # 只保留数值列
                temp = temp.select_dtypes(include=[np.number])
                standardized[name] = temp

            if len(standardized) < 2:
                self.logger.warning("有效数据源不足两个，无法进行交叉验证")
                if standardized:
                    name, df = list(standardized.items())[0]
                    result = df.reset_index()
                    result["_data_source"] = "交叉验证"
                    return result, []
                return pd.DataFrame(), []

            # 对齐日期索引：取所有数据源日期的交集
            common_dates = None
            for name, df in standardized.items():
                if common_dates is None:
                    common_dates = set(df.index)
                else:
                    common_dates = common_dates.intersection(set(df.index))

            if not common_dates:
                self.logger.warning("各数据源无共同日期，无法交叉验证")
                return pd.DataFrame(), []

            common_dates = sorted(common_dates)

            # 获取所有数据源共有的数值列
            all_numeric_cols = None
            for name, df in standardized.items():
                cols = set(df.columns)
                if all_numeric_cols is None:
                    all_numeric_cols = cols
                else:
                    all_numeric_cols = all_numeric_cols.intersection(cols)

            if not all_numeric_cols:
                self.logger.warning("各数据源无共同数值列，无法交叉验证")
                return pd.DataFrame(), []

            all_numeric_cols = sorted(all_numeric_cols)

            # 对每个日期、每个数值列进行交叉验证
            merged_data = []
            source_tags = []

            for date in common_dates:
                row_data = {}
                has_conflict = False

                for col in all_numeric_cols:
                    values = {}
                    for name, df in standardized.items():
                        if date in df.index and col in df.columns:
                            val = df.loc[date, col]
                            if not pd.isna(val):
                                values[name] = val

                    if len(values) < 2:
                        # 只有一个数据源有值，直接使用
                        if values:
                            row_data[col] = list(values.values())[0]
                        else:
                            row_data[col] = np.nan
                    else:
                        # 多个数据源有值，检查差异
                        vals = list(values.values())
                        val_min = min(vals)
                        val_max = max(vals)

                        # 计算差异百分比（相对于均值的偏差）
                        val_mean = np.mean(vals)
                        if val_mean != 0:
                            diff_pct = abs(val_max - val_min) / abs(val_mean) * 100
                        else:
                            diff_pct = 0.0 if val_max == val_min else 100.0

                        if diff_pct > threshold:
                            has_conflict = True
                            conflict_info.append({
                                "date": date,
                                "column": col,
                                "sources": values,
                                "diff_pct": round(diff_pct, 4),
                            })

                        # 取中位数作为最终值
                        row_data[col] = np.median(vals)

                row_data["日期"] = date
                merged_data.append(row_data)
                source_tags.append("数据冲突" if has_conflict else "交叉验证")

            merged_df = pd.DataFrame(merged_data)
            merged_df["_data_source"] = source_tags

            # 调整列顺序：日期在前，_data_source 在后
            cols = ["日期"] + [c for c in all_numeric_cols] + ["_data_source"]
            merged_df = merged_df[cols]

            self.logger.info(
                "交叉验证完成，总行数: %d，冲突行数: %d，冲突记录数: %d",
                len(merged_df),
                sum(1 for t in source_tags if t == "数据冲突"),
                len(conflict_info),
            )
            return merged_df, conflict_info

        except Exception as e:
            self.logger.error("交叉验证失败，异常: %s", e)
            return pd.DataFrame(), []

    def calculate_quality_score(self, df, source_count=1, conflict_count=0):
        """计算数据质量评分。

        综合数据完整性、来源数量和交叉验证一致性三个维度，
        计算数据质量的综合评分。

        Args:
            df (pandas.DataFrame): 待评估的数据。
            source_count (int): 数据来源数量，默认为 1。
            conflict_count (int): 交叉验证冲突数，默认为 0。

        Returns:
            float: 质量评分，范围 0-100。如果输入为空，返回 0.0。
        """
        if df is None or df.empty:
            self.logger.warning("calculate_quality_score 接收到空 DataFrame，返回 0.0")
            return 0.0

        try:
            # 1. 数据完整性评分（40%权重）
            total_cells = df.shape[0] * df.shape[1]
            if total_cells == 0:
                completeness_score = 0.0
            else:
                non_null_count = df.notna().sum().sum()
                completeness_ratio = non_null_count / total_cells
                completeness_score = completeness_ratio * 100

            # 2. 来源数量评分（30%权重）
            if source_count <= 1:
                source_score = 60.0
            elif source_count == 2:
                source_score = 80.0
            else:
                source_score = 100.0

            # 3. 交叉验证一致性评分（30%权重）
            total_rows = len(df)
            if total_rows == 0:
                consistency_score = 100.0
            else:
                conflict_ratio = conflict_count / total_rows
                consistency_score = max(0.0, (1 - conflict_ratio) * 100)

            # 综合评分
            quality_score = (
                completeness_score * 0.4
                + source_score * 0.3
                + consistency_score * 0.3
            )

            quality_score = round(quality_score, 2)
            self.logger.info(
                "数据质量评分: %.2f（完整性: %.2f，来源: %.2f，一致性: %.2f）",
                quality_score, completeness_score, source_score, consistency_score,
            )
            return quality_score

        except Exception as e:
            self.logger.error("计算质量评分失败，异常: %s", e)
            return 0.0

    def generate_quality_report(self, df, source_count=1, conflict_info=None):
        """生成数据质量报告。

        对 DataFrame 进行全面的质量评估，返回包含评分、行数统计、
        缺失率、来源数量、冲突数等信息的字典。

        Args:
            df (pandas.DataFrame): 待评估的数据。
            source_count (int): 数据来源数量，默认为 1。
            conflict_info (list, optional): 交叉验证冲突信息列表。
                默认为 None，表示无冲突。

        Returns:
            dict: 质量报告字典，包含以下字段：
                - score: 质量评分（float）
                - total_rows: 总行数（int）
                - complete_rows: 完整行数（int）
                - missing_ratio: 缺失率（float）
                - source_count: 数据来源数（int）
                - conflict_count: 冲突数（int）
                - filled_count: 补全数据行数（int）
                - details: 详细信息（dict）
        """
        if conflict_info is None:
            conflict_info = []

        if df is None or df.empty:
            self.logger.warning("generate_quality_report 接收到空 DataFrame")
            return {
                "score": 0.0,
                "total_rows": 0,
                "complete_rows": 0,
                "missing_ratio": 1.0,
                "source_count": source_count,
                "conflict_count": len(conflict_info),
                "filled_count": 0,
                "details": {},
            }

        try:
            total_rows = len(df)
            complete_rows = int(df.dropna().shape[0])

            # 计算缺失率
            total_cells = df.shape[0] * df.shape[1]
            if total_cells == 0:
                missing_ratio = 1.0
            else:
                missing_cells = df.isna().sum().sum()
                missing_ratio = round(missing_cells / total_cells, 4)

            # 统计补全数据行数
            if "_data_source" in df.columns:
                filled_count = int((df["_data_source"] == "补全").sum())
            else:
                filled_count = 0

            conflict_count = len(conflict_info)

            # 计算质量评分
            score = self.calculate_quality_score(
                df, source_count=source_count, conflict_count=conflict_count,
            )

            # 详细信息
            details = {
                "completeness": round(1 - missing_ratio, 4),
                "source_score": (
                    60.0 if source_count <= 1
                    else (80.0 if source_count == 2 else 100.0)
                ),
                "consistency_score": max(
                    0.0, (1 - conflict_count / total_rows) * 100,
                ) if total_rows > 0 else 100.0,
                "missing_per_column": {
                    col: int(df[col].isna().sum()) for col in df.columns
                },
            }

            report = {
                "score": score,
                "total_rows": total_rows,
                "complete_rows": complete_rows,
                "missing_ratio": missing_ratio,
                "source_count": source_count,
                "conflict_count": conflict_count,
                "filled_count": filled_count,
                "details": details,
            }

            self.logger.info(
                "数据质量报告生成完成，评分: %.2f，总行数: %d，缺失率: %.2f%%",
                score, total_rows, missing_ratio * 100,
            )
            return report

        except Exception as e:
            self.logger.error("生成质量报告失败，异常: %s", e)
            return {
                "score": 0.0,
                "total_rows": 0,
                "complete_rows": 0,
                "missing_ratio": 1.0,
                "source_count": source_count,
                "conflict_count": len(conflict_info),
                "filled_count": 0,
                "details": {},
            }
