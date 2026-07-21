"""
日志面板

显示结构化的日志条目列表。
支持按级别过滤。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QComboBox, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from src.logger import get_logger

logger = get_logger("gui.log_panel")


class LogPanel(QWidget):
    """
    日志面板

    以列表形式显示结构化日志。
    支持按日志级别过滤。
    """

    LEVEL_COLORS = {
        "DEBUG": QColor("#585b70"),
        "INFO": QColor("#a6e3a1"),
        "WARNING": QColor("#f9e2af"),
        "ERROR": QColor("#f38ba8"),
        "CRITICAL": QColor("#cba6f7"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题和过滤
        header = QHBoxLayout()

        title = QLabel("日志")
        title.setStyleSheet("font-weight: bold; color: #89b4fa;")
        header.addWidget(title)

        header.addWidget(QLabel("过滤:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        header.addWidget(self.filter_combo)

        header.addStretch()

        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self.clear)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        # 日志列表
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("""
            QListWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #1e1e2e;
            }
            QListWidget::item:selected {
                background-color: #313244;
            }
        """)
        layout.addWidget(self.log_list)

        self._current_filter = "全部"

    def add_log(self, level: str, message: str):
        """
        添加日志条目

        Args:
            level: 日志级别
            message: 日志消息
        """
        if self._current_filter != "全部" and level != self._current_filter:
            return

        item_text = f"[{level}] {message}"
        item = QListWidgetItem(item_text)

        color = self.LEVEL_COLORS.get(level, QColor("#cdd6f4"))
        item.setForeground(color)

        self.log_list.addItem(item)

        # 自动滚动
        self.log_list.scrollToBottom()

    def clear(self):
        """清空日志列表"""
        self.log_list.clear()

    def _on_filter_changed(self, filter_text: str):
        """过滤变化时的回调"""
        self._current_filter = filter_text
        self.clear()
