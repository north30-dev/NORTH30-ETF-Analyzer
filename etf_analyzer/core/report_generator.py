# -*- coding: utf-8 -*-
"""
ETF分析器报告生成模块

本模块提供PDF报告生成功能，基于reportlab库生成包含关键指标概览、
图表展示和综合分析文字的ETF分析报告。支持自定义报告模块选择，
自动注册中文字体，生成专业排版的PDF文档。
"""

import os
import tempfile
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from etf_analyzer.config import (
    REPORT_DIR_PATH,
    REPORT_FONT,
    REPORT_FONT_SIZE,
    REPORT_TITLE_FONT_SIZE,
    ensure_dirs,
)
from etf_analyzer.logger import setup_logger
from etf_analyzer.visualizer import ETFVisualizer

logger = setup_logger("report_generator")

# 报告可选模块列表
AVAILABLE_MODULES = ["nav_trend", "holdings", "industry", "risk", "performance"]

# 模块标题映射
MODULE_TITLES = {
    "nav_trend": "净值走势分析",
    "holdings": "成分股构成分析",
    "industry": "行业分布统计",
    "risk": "风险指标分析",
    "performance": "绩效分析",
}


class ReportGenerator:
    """ETF分析报告生成器，基于reportlab生成PDF格式的分析报告。

    该类封装了PDF报告生成的完整流程，包括封面页、关键指标概览、
    图表嵌入和综合分析文字等模块，支持自定义选择报告内容模块，
    自动处理中文字体注册和页面排版。

    Attributes:
        logger: 日志记录器实例。
        output_dir: 报告输出目录路径。
        font_name: 已注册的中文字体名称。
        page_size: 页面尺寸，默认为A4。
        visualizer: ETFVisualizer 实例，用于生成图表。
        styles: reportlab 样式表。
    """

    def __init__(self):
        """初始化报告生成器。

        设置日志记录器、输出目录、注册中文字体并初始化页面尺寸。
        优先尝试注册SimHei TTF字体，如果失败则使用reportlab内置的
        CIDFont('STSong-Light')作为后备字体。
        """
        self.logger = logger
        self.output_dir = REPORT_DIR_PATH
        ensure_dirs()

        # 注册中文字体
        self.font_name = self._register_chinese_font()

        # 页面尺寸
        self.page_size = A4

        # 初始化可视化器
        self.visualizer = ETFVisualizer()

        # 初始化样式表
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

        self.logger.info("报告生成器初始化完成，字体: %s", self.font_name)

    def _register_chinese_font(self):
        """注册中文字体，优先使用SimHei TTF字体，失败则使用CIDFont后备。

        尝试从Windows字体目录加载SimHei字体文件（simhei.ttf），
        如果文件不存在或加载失败，则回退到reportlab内置的
        STSong-Light CID字体。

        Returns:
            str: 成功注册的字体名称，用于后续PDF文本渲染。
        """
        font_name = REPORT_FONT  # "SimHei"

        # 尝试注册SimHei TTF字体
        simhei_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"),
                                   "Fonts", "simhei.ttf")

        try:
            if os.path.isfile(simhei_path):
                pdfmetrics.registerFont(TTFont(font_name, simhei_path))
                self.logger.info("成功注册SimHei TTF字体: %s", simhei_path)
                return font_name
        except Exception as e:
            self.logger.warning("注册SimHei TTF字体失败: %s，将使用CIDFont后备", e)

        # 使用CIDFont后备
        try:
            fallback_name = "STSong-Light"
            pdfmetrics.registerFont(UnicodeCIDFont(fallback_name))
            self.logger.info("使用CIDFont后备字体: %s", fallback_name)
            return fallback_name
        except Exception as e:
            self.logger.error("注册CIDFont后备字体也失败: %s", e)
            return "Helvetica"

    def _setup_custom_styles(self):
        """设置自定义PDF样式，包括标题、正文和表格等样式。

        在reportlab默认样式表的基础上，添加中文字体支持的自定义样式，
        包括报告标题、章节标题、正文段落和表格内容等样式。
        """
        font = self.font_name

        # 报告大标题样式
        self.styles.add(ParagraphStyle(
            name="ReportTitle",
            fontName=font,
            fontSize=REPORT_TITLE_FONT_SIZE,
            leading=REPORT_TITLE_FONT_SIZE * 1.5,
            alignment=1,  # 居中
            spaceAfter=20,
            textColor=colors.HexColor("#1a1a2e"),
        ))

        # 章节标题样式
        self.styles.add(ParagraphStyle(
            name="SectionTitle",
            fontName=font,
            fontSize=14,
            leading=20,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#16213e"),
        ))

        # 正文段落样式
        self.styles.add(ParagraphStyle(
            name="BodyText_CN",
            fontName=font,
            fontSize=REPORT_FONT_SIZE,
            leading=REPORT_FONT_SIZE * 1.6,
            spaceBefore=4,
            spaceAfter=4,
            firstLineIndent=24,
            textColor=colors.HexColor("#333333"),
        ))

        # 表格内容样式
        self.styles.add(ParagraphStyle(
            name="TableCell",
            fontName=font,
            fontSize=10,
            leading=14,
            alignment=1,  # 居中
        ))

    def generate_report(self, symbol, analysis_results, modules=None, output_filename=None):
        """生成完整的ETF分析PDF报告。

        根据指定的ETF代码、分析结果数据和模块选择，生成包含封面页、
        关键指标概览、图表展示和综合分析文字的PDF报告文件。

        Args:
            symbol (str): ETF代码，例如 "510300"。
            analysis_results (dict): 分析结果字典，包含各模块的分析数据。
                常见键包括: "nav_data"(净值数据), "holdings_data"(持仓数据),
                "industry_data"(行业数据), "risk_metrics"(风险指标),
                "performance_metrics"(业绩指标) 等。
            modules (list, optional): 选择的报告模块列表，默认为None表示包含所有模块。
                可选值: ["nav_trend", "holdings", "industry", "risk", "performance"]。
            output_filename (str, optional): 输出文件名，默认为None时自动生成。
                自动生成格式: "{symbol}_report_{日期}.pdf"。

        Returns:
            str: 生成的PDF文件绝对路径。

        Raises:
            ValueError: 当symbol为空或analysis_results不是字典时抛出。
            RuntimeError: 当PDF生成过程中发生严重错误时抛出。
        """
        if not symbol:
            raise ValueError("ETF代码不能为空")
        if not isinstance(analysis_results, dict):
            raise ValueError("analysis_results 必须是字典类型")

        self.logger.info("开始生成报告，ETF代码: %s，模块: %s", symbol, modules)

        # 确定输出文件名
        if output_filename is None:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{symbol}_report_{date_str}.pdf"

        output_path = os.path.join(self.output_dir, output_filename)
        chart_paths = {}

        try:
            # 构建PDF文档
            doc = SimpleDocTemplate(
                output_path,
                pagesize=self.page_size,
                leftMargin=2 * cm,
                rightMargin=2 * cm,
                topMargin=2.5 * cm,
                bottomMargin=2 * cm,
            )

            # 生成临时图表文件
            chart_paths = self._generate_temp_charts(symbol, analysis_results, modules)

            # 构建报告内容
            story = self._build_report_modules(symbol, analysis_results, modules, chart_paths)

            # 生成PDF，带页眉页脚
            doc.build(story, onFirstPage=self._add_header_footer,
                      onLaterPages=self._add_header_footer)

            self.logger.info("报告生成成功: %s", output_path)
            return output_path

        except Exception as e:
            self.logger.error("生成PDF报告时发生错误: %s", e)
            raise RuntimeError(f"生成PDF报告失败: {e}") from e

        finally:
            # 清理临时图表文件
            self._cleanup_temp_charts(chart_paths)

    def _add_overview_section(self, story, symbol, analysis_results):
        """添加关键指标概览部分到报告。

        以表格形式展示ETF的核心指标，包括累计收益率、年化收益率、
        年化波动率、最大回撤和夏普比率等，便于快速了解ETF的整体表现。

        Args:
            story (list): reportlab的Story列表，PDF元素将追加到此列表。
            symbol (str): ETF代码，用于表格标题显示。
            analysis_results (dict): 分析结果字典，从中提取风险和业绩指标。
        """
        story.append(Paragraph("关键指标概览", self.styles["SectionTitle"]))
        story.append(Spacer(1, 8))

        # 提取指标数据
        risk_metrics = analysis_results.get("risk_metrics", {})
        performance_metrics = analysis_results.get("performance_metrics", {})

        # 构建指标行数据
        indicators = [
            ("累计收益率", performance_metrics.get("cumulative_return", None)),
            ("年化收益率", performance_metrics.get("annualized_return", None)),
            ("年化波动率", risk_metrics.get("annualized_volatility", None)),
            ("最大回撤", risk_metrics.get("max_drawdown", None)),
            ("夏普比率", risk_metrics.get("sharpe_ratio", None)),
        ]

        # 构建表格数据
        table_data = [["指标", "数值"]]
        for name, value in indicators:
            formatted_value = self._format_percentage(value) if value is not None else "—"
            table_data.append([name, formatted_value])

        # 创建表格
        col_widths = [8 * cm, 8 * cm]
        table = Table(table_data, colWidths=col_widths)

        # 设置表格样式
        table_style = TableStyle([
            # 表头样式
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), self.font_name),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("FONTSIZE", (0, 1), (-1, -1), 11),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWHEIGHT", (0, 0), (-1, -1), 28),
            # 边框
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1a1a2e")),
            # 奇偶行交替背景
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0f4f8")),
            ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#f0f4f8")),
            ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#f0f4f8")),
            # 上下间距
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
        table.setStyle(table_style)

        story.append(table)
        story.append(Spacer(1, 16))

    def _add_chart_section(self, story, title, image_path):
        """添加图表章节到报告，嵌入图片并设置标题。

        在报告中添加一个图表章节，包含章节标题和嵌入的图片。
        图片宽度自动适配页面宽度，如果图片文件不存在则显示提示文字。

        Args:
            story (list): reportlab的Story列表，PDF元素将追加到此列表。
            title (str): 章节标题文字。
            image_path (str): 图片文件的绝对路径，支持PNG、JPG等格式。
        """
        story.append(Paragraph(title, self.styles["SectionTitle"]))
        story.append(Spacer(1, 8))

        if image_path and os.path.isfile(image_path):
            try:
                # 计算可用宽度，适配页面
                available_width = self.page_size[0] - 4 * cm  # 减去左右边距
                img = Image(image_path, width=available_width, height=available_width * 0.5)
                img.hAlign = "CENTER"
                story.append(img)
                story.append(Spacer(1, 12))
                self.logger.debug("图表嵌入成功: %s", image_path)
            except Exception as e:
                self.logger.warning("嵌入图表失败: %s", e)
                story.append(Paragraph(
                    f"[图表加载失败: {title}]",
                    self.styles["BodyText_CN"]
                ))
                story.append(Spacer(1, 12))
        else:
            story.append(Paragraph(
                f"[暂无图表数据: {title}]",
                self.styles["BodyText_CN"]
            ))
            story.append(Spacer(1, 12))

    def _add_text_analysis(self, story, symbol, analysis_results):
        """添加综合分析文字部分到报告。

        根据分析结果数据生成文字分析内容，包括净值趋势分析、
        风险评估和持仓结构分析三个维度的文字描述。

        Args:
            story (list): reportlab的Story列表，PDF元素将追加到此列表。
            symbol (str): ETF代码，用于分析文字中的引用。
            analysis_results (dict): 分析结果字典，从中提取各维度数据
                以生成对应的分析文字。
        """
        story.append(Paragraph("综合分析", self.styles["SectionTitle"]))
        story.append(Spacer(1, 8))

        # 净值趋势分析
        nav_text = self._generate_nav_analysis_text(symbol, analysis_results)
        story.append(Paragraph(nav_text, self.styles["BodyText_CN"]))
        story.append(Spacer(1, 8))

        # 风险评估
        risk_text = self._generate_risk_analysis_text(symbol, analysis_results)
        story.append(Paragraph(risk_text, self.styles["BodyText_CN"]))
        story.append(Spacer(1, 8))

        # 持仓结构分析
        holdings_text = self._generate_holdings_analysis_text(symbol, analysis_results)
        story.append(Paragraph(holdings_text, self.styles["BodyText_CN"]))
        story.append(Spacer(1, 12))

    def _build_report_modules(self, symbol, analysis_results, modules, chart_paths=None):
        """根据模块选择构建报告内容。

        根据用户指定的模块列表，选择性地构建报告的各个章节，
        包括封面页、关键指标概览、各模块图表和综合分析文字。

        Args:
            symbol (str): ETF代码。
            analysis_results (dict): 分析结果字典。
            modules (list or None): 选择的报告模块列表，None表示包含所有模块。
            chart_paths (dict or None): 图表文件路径字典，None时自动生成。

        Returns:
            list: reportlab的Story列表，包含所有PDF元素。
        """
        story = []

        # 确定要包含的模块
        if modules is None:
            modules = AVAILABLE_MODULES[:]
        else:
            modules = [m for m in modules if m in AVAILABLE_MODULES]

        # 如果未提供图表路径，则生成临时图表
        if chart_paths is None:
            chart_paths = self._generate_temp_charts(symbol, analysis_results, modules)

        # 封面页
        self._add_title_page(story, symbol)
        story.append(PageBreak())

        # 目录页
        self._add_toc_page(story, modules)
        story.append(PageBreak())

        # 关键指标概览
        self._add_overview_section(story, symbol, analysis_results)

        # 各模块图表
        module_chart_map = {
            "nav_trend": ("净值走势分析", chart_paths.get("nav_trend")),
            "holdings": ("前十大持仓分析", chart_paths.get("holdings")),
            "industry": ("行业分布分析", chart_paths.get("industry")),
            "risk": ("风险分析", chart_paths.get("risk")),
            "performance": ("业绩表现分析", chart_paths.get("performance")),
        }

        for module_name in modules:
            if module_name in module_chart_map:
                title, chart_path = module_chart_map[module_name]
                self._add_chart_section(story, title, chart_path)

        # 综合分析文字
        self._add_text_analysis(story, symbol, analysis_results)

        return story

    def _add_title_page(self, story, symbol):
        """添加报告封面页。

        在报告开头添加封面页，包含报告标题、ETF代码和生成日期，
        使用居中排版和较大字号突出显示。

        Args:
            story (list): reportlab的Story列表，封面页元素将追加到此列表。
            symbol (str): ETF代码，显示在封面页上。
        """
        story.append(Spacer(1, 120))
        story.append(Paragraph("ETF分析报告", self.styles["ReportTitle"]))
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            f"ETF代码: {symbol}",
            self.styles["ReportTitle"]
        ))
        story.append(Spacer(1, 20))
        story.append(Paragraph(
            f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles["ReportTitle"]
        ))

    def _add_toc_page(self, story, modules):
        """添加目录页。

        在封面页之后、正文之前添加目录页，根据选择的模块动态生成目录条目。

        Args:
            story (list): reportlab的Story列表，目录页元素将追加到此列表。
            modules (list): 选择的报告模块列表，用于生成对应的目录条目。
        """
        story.append(Spacer(1, 40))
        story.append(Paragraph("目  录", self.styles["ReportTitle"]))
        story.append(Spacer(1, 24))

        # 构建目录表格数据
        table_data = [["序号", "章节名称"]]
        for idx, module_name in enumerate(modules, start=1):
            title = MODULE_TITLES.get(module_name, module_name)
            table_data.append([str(idx), title])

        # 创建目录表格
        col_widths = [2 * cm, 14 * cm]
        table = Table(table_data, colWidths=col_widths)

        # 设置表格样式
        table_style = TableStyle([
            # 表头样式
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), self.font_name),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("FONTSIZE", (0, 1), (-1, -1), 11),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWHEIGHT", (0, 0), (-1, -1), 28),
            # 边框
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1a1a2e")),
            # 奇偶行交替背景
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0f4f8")),
            ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#f0f4f8")),
            ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#f0f4f8")),
            # 上下间距
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            # 左侧缩进
            ("LEFTPADDING", (1, 0), (1, -1), 12),
        ])
        table.setStyle(table_style)

        story.append(table)

    def _add_header_footer(self, canvas, doc):
        """添加页眉和页脚。

        在PDF每一页的顶部添加报告标题页眉，底部添加页码页脚。
        首页和后续页均会添加页眉页脚。

        Args:
            canvas: reportlab的Canvas对象，用于绘制页眉页脚。
            doc: reportlab的DocTemplate对象，提供页面尺寸等信息。
        """
        canvas.saveState()

        # 页眉
        canvas.setFont(self.font_name, 9)
        canvas.setFillColor(colors.HexColor("#666666"))
        header_text = f"ETF分析报告"
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin - 10 * mm,
                          header_text)
        # 页眉下划线
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, doc.height + doc.topMargin - 12 * mm,
                     doc.width + doc.leftMargin, doc.height + doc.topMargin - 12 * mm)

        # 页脚页码
        canvas.setFont(self.font_name, 9)
        canvas.setFillColor(colors.HexColor("#666666"))
        page_num = canvas.getPageNumber()
        footer_text = f"— {page_num} —"
        canvas.drawCentredString(doc.width / 2 + doc.leftMargin,
                                  doc.bottomMargin - 10 * mm, footer_text)

        canvas.restoreState()

    def _format_percentage(self, value):
        """格式化百分比数值。

        将数值格式化为百分比字符串，保留两位小数并添加百分号。
        对于None值返回"—"，对于非数值类型尝试转换后格式化。

        Args:
            value (float or int or None): 待格式化的数值，可以是百分比形式的
                小数（如0.05表示5%）或已乘100的数值（如5表示5%）。

        Returns:
            str: 格式化后的百分比字符串，例如 "5.00%" 或 "—"。
        """
        if value is None:
            return "—"

        try:
            num = float(value)
            # 判断数值大小：如果绝对值大于1，认为已经是百分比形式
            if abs(num) > 1:
                return f"{num:.2f}%"
            else:
                return f"{num * 100:.2f}%"
        except (ValueError, TypeError):
            return "—"

    def _generate_temp_charts(self, symbol, analysis_results, modules):
        """生成临时图表文件用于嵌入PDF。

        调用ETFVisualizer的方法生成各模块对应的图表，保存为临时文件。
        返回图表文件路径字典，键为模块名称，值为图片文件路径。

        Args:
            symbol (str): ETF代码，用于图表标题显示。
            analysis_results (dict): 分析结果字典，提供图表绘制所需的数据。
            modules (list or None): 选择的报告模块列表，None表示生成所有模块的图表。

        Returns:
            dict: 图表文件路径字典，键为模块名称（如"nav_trend"），
                值为对应的图片文件绝对路径。如果某个模块的数据不足，
                对应值为None。
        """
        if modules is None:
            modules = AVAILABLE_MODULES[:]

        chart_paths = {}
        temp_dir = tempfile.gettempdir()

        try:
            # 净值走势图
            if "nav_trend" in modules:
                nav_data = analysis_results.get("nav_data")
                if nav_data is not None and not nav_data.empty:
                    path = os.path.join(temp_dir, f"etf_{symbol}_nav_trend.png")
                    try:
                        self.visualizer.plot_nav_trend(
                            nav_data, symbol=symbol,
                            save_path=path, show=False
                        )
                        chart_paths["nav_trend"] = path
                        self.logger.debug("净值走势图已生成: %s", path)
                    except Exception as e:
                        self.logger.warning("生成净值走势图失败: %s", e)
                        chart_paths["nav_trend"] = None
                else:
                    chart_paths["nav_trend"] = None

            # 持仓柱状图
            if "holdings" in modules:
                holdings_data = analysis_results.get("holdings_data")
                if holdings_data is not None and not holdings_data.empty:
                    path = os.path.join(temp_dir, f"etf_{symbol}_holdings.png")
                    try:
                        self.visualizer.plot_holdings_bar(
                            holdings_data, symbol=symbol,
                            save_path=path, show=False
                        )
                        chart_paths["holdings"] = path
                        self.logger.debug("持仓柱状图已生成: %s", path)
                    except Exception as e:
                        self.logger.warning("生成持仓柱状图失败: %s", e)
                        chart_paths["holdings"] = None
                else:
                    chart_paths["holdings"] = None

            # 行业分布饼图
            if "industry" in modules:
                industry_data = analysis_results.get("industry_data")
                if industry_data is not None and not industry_data.empty:
                    path = os.path.join(temp_dir, f"etf_{symbol}_industry.png")
                    try:
                        self.visualizer.plot_industry_pie(
                            industry_data, symbol=symbol,
                            save_path=path, show=False
                        )
                        chart_paths["industry"] = path
                        self.logger.debug("行业分布饼图已生成: %s", path)
                    except Exception as e:
                        self.logger.warning("生成行业分布饼图失败: %s", e)
                        chart_paths["industry"] = None
                else:
                    chart_paths["industry"] = None

            # 风险分析图（回撤曲线）
            if "risk" in modules:
                nav_data = analysis_results.get("nav_data")
                if nav_data is not None and not nav_data.empty:
                    path = os.path.join(temp_dir, f"etf_{symbol}_risk.png")
                    try:
                        self.visualizer.plot_drawdown(
                            nav_data, symbol=symbol,
                            save_path=path, show=False
                        )
                        chart_paths["risk"] = path
                        self.logger.debug("回撤曲线图已生成: %s", path)
                    except Exception as e:
                        self.logger.warning("生成回撤曲线图失败: %s", e)
                        chart_paths["risk"] = None
                else:
                    chart_paths["risk"] = None

            # 业绩表现图（K线图）
            if "performance" in modules:
                nav_data = analysis_results.get("nav_data")
                if nav_data is not None and not nav_data.empty:
                    path = os.path.join(temp_dir, f"etf_{symbol}_performance.png")
                    try:
                        self.visualizer.plot_kline(
                            nav_data, symbol=symbol,
                            save_path=path, show=False
                        )
                        chart_paths["performance"] = path
                        self.logger.debug("K线图已生成: %s", path)
                    except Exception as e:
                        self.logger.warning("生成K线图失败: %s", e)
                        chart_paths["performance"] = None
                else:
                    chart_paths["performance"] = None

        except Exception as e:
            self.logger.error("生成临时图表时发生错误: %s", e)

        return chart_paths

    def _cleanup_temp_charts(self, chart_paths):
        """清理临时图表文件。

        删除生成报告过程中创建的临时图片文件，释放磁盘空间。

        Args:
            chart_paths (dict): 图表文件路径字典，键为模块名称，值为文件路径。
        """
        if not chart_paths:
            return

        for name, path in chart_paths.items():
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                    self.logger.debug("已清理临时图表: %s", path)
                except OSError as e:
                    self.logger.warning("清理临时图表失败: %s - %s", path, e)

    def _generate_nav_analysis_text(self, symbol, analysis_results):
        """生成净值趋势分析文字。

        根据净值数据和业绩指标，生成描述性的净值趋势分析文字段落。

        Args:
            symbol (str): ETF代码。
            analysis_results (dict): 分析结果字典。

        Returns:
            str: 净值趋势分析文字内容。
        """
        performance = analysis_results.get("performance_metrics", {})
        risk = analysis_results.get("risk_metrics", {})

        cumulative_return = performance.get("cumulative_return")
        annualized_return = performance.get("annualized_return")

        parts = [f"{symbol}净值趋势分析："]

        if cumulative_return is not None:
            parts.append(f"该ETF累计收益率为{self._format_percentage(cumulative_return)}，")
        else:
            parts.append("该ETF累计收益率数据暂无，")

        if annualized_return is not None:
            parts.append(f"年化收益率为{self._format_percentage(annualized_return)}，")
        else:
            parts.append("年化收益率数据暂无，")

        max_dd = risk.get("max_drawdown")
        if max_dd is not None:
            parts.append(f"期间最大回撤为{self._format_percentage(max_dd)}。")
        else:
            parts.append("最大回撤数据暂无。")

        # 简单趋势判断
        if cumulative_return is not None:
            try:
                cr = float(cumulative_return)
                if abs(cr) > 1:
                    cr_pct = cr
                else:
                    cr_pct = cr * 100

                if cr_pct > 20:
                    parts.append("整体表现较为强劲，净值呈明显上升趋势。")
                elif cr_pct > 0:
                    parts.append("整体呈温和上涨态势。")
                elif cr_pct > -10:
                    parts.append("整体表现偏弱，净值小幅下行。")
                else:
                    parts.append("整体表现不佳，净值出现较大幅度下跌。")
            except (ValueError, TypeError):
                pass

        return "".join(parts)

    def _generate_risk_analysis_text(self, symbol, analysis_results):
        """生成风险评估分析文字。

        根据风险指标数据，生成描述性的风险评估分析文字段落。

        Args:
            symbol (str): ETF代码。
            analysis_results (dict): 分析结果字典。

        Returns:
            str: 风险评估分析文字内容。
        """
        risk = analysis_results.get("risk_metrics", {})

        volatility = risk.get("annualized_volatility")
        sharpe = risk.get("sharpe_ratio")
        max_dd = risk.get("max_drawdown")

        parts = [f"{symbol}风险评估："]

        if volatility is not None:
            parts.append(f"年化波动率为{self._format_percentage(volatility)}，")
        else:
            parts.append("年化波动率数据暂无，")

        if sharpe is not None:
            parts.append(f"夏普比率为{self._format_percentage(sharpe) if abs(float(sharpe)) > 1 else f'{float(sharpe):.2f}'}，")
        else:
            parts.append("夏普比率数据暂无，")

        if max_dd is not None:
            parts.append(f"最大回撤为{self._format_percentage(max_dd)}。")
        else:
            parts.append("最大回撤数据暂无。")

        # 风险等级判断
        if volatility is not None:
            try:
                vol = float(volatility)
                if abs(vol) > 1:
                    vol_pct = vol
                else:
                    vol_pct = vol * 100

                if vol_pct < 10:
                    parts.append("整体波动较低，风险较小，适合稳健型投资者。")
                elif vol_pct < 20:
                    parts.append("波动处于中等水平，风险适中。")
                else:
                    parts.append("波动较大，风险较高，投资者需谨慎。")
            except (ValueError, TypeError):
                pass

        return "".join(parts)

    def _generate_holdings_analysis_text(self, symbol, analysis_results):
        """生成持仓结构分析文字。

        根据持仓数据和行业分布数据，生成描述性的持仓结构分析文字段落。

        Args:
            symbol (str): ETF代码。
            analysis_results (dict): 分析结果字典。

        Returns:
            str: 持仓结构分析文字内容。
        """
        holdings_data = analysis_results.get("holdings_data")
        industry_data = analysis_results.get("industry_data")

        parts = [f"{symbol}持仓结构分析："]

        # 持仓集中度分析
        if holdings_data is not None and not holdings_data.empty:
            weight_col = None
            for col_name in ["weight", "占比", "持仓占比", "比例", "holding"]:
                if col_name in holdings_data.columns:
                    weight_col = col_name
                    break

            if weight_col is not None:
                try:
                    import pandas as pd
                    top_weights = pd.to_numeric(holdings_data[weight_col], errors="coerce")
                    top10_sum = top_weights.head(10).sum()
                    parts.append(f"前十大重仓股合计占比约{top10_sum:.2f}%，")

                    if top10_sum > 60:
                        parts.append("持仓集中度较高，个股风险较大。")
                    elif top10_sum > 40:
                        parts.append("持仓集中度适中。")
                    else:
                        parts.append("持仓较为分散，个股风险较低。")
                except Exception:
                    parts.append("持仓数据解析异常。")
            else:
                parts.append("持仓占比数据暂无。")
        else:
            parts.append("持仓数据暂无，")

        # 行业分布分析
        if industry_data is not None and not industry_data.empty:
            industry_col = None
            weight_col = None
            for col_name in ["industry", "行业", "行业名称", "行业分类"]:
                if col_name in industry_data.columns:
                    industry_col = col_name
                    break
            for col_name in ["weight", "占比", "持仓占比", "比例", "holding"]:
                if col_name in industry_data.columns:
                    weight_col = col_name
                    break

            if industry_col is not None and weight_col is not None:
                try:
                    import pandas as pd
                    industry_weights = pd.to_numeric(industry_data[weight_col], errors="coerce")
                    top_industry_idx = industry_weights.idxmax()
                    top_industry_name = industry_data.loc[top_industry_idx, industry_col]
                    top_industry_weight = industry_weights.max()
                    parts.append(f"第一大重仓行业为{top_industry_name}，"
                                 f"占比约{top_industry_weight:.2f}%。")
                except Exception:
                    parts.append("行业分布数据解析异常。")
            else:
                parts.append("行业分布详情暂无。")
        else:
            parts.append("行业分布数据暂无。")

        return "".join(parts)
