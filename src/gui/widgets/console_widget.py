"""
控制台小部件

显示 ComfyUI 输出的实时控制台。
支持滚动、清空和日志复制。
"""

from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QWidget
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from src.logger import get_logger

logger = get_logger("gui.console")


class ConsoleWidget(QWidget):
    """
    控制台小部件

    用于显示 ComfyUI 的实时输出日志。
    支持自动滚动、清空和日志复制。
    """

    # 信号：当有新日志时触发
    log_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setObjectName("consoleClearBtn")
        self.btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(self.btn_clear)

        self.btn_copy = QPushButton("复制日志")
        self.btn_copy.setObjectName("consoleCopyBtn")
        self.btn_copy.clicked.connect(self._copy_log)
        toolbar.addWidget(self.btn_copy)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 控制台输出区域
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.output)

    def append_log(self, message: str):
        """
        追加日志消息

        Args:
            message: 日志消息
        """
        self.output.append(message)
        self.log_received.emit(message)

        # 自动滚动到底部
        scrollbar = self.output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """清空控制台"""
        self.output.clear()

    def _copy_log(self):
        """复制日志到剪贴板"""
        self.output.selectAll()
        self.output.copy()
        self.output.deselect(self.output.textCursor().anchor())

    def set_color_message(self, message: str, color: str):
        """
        添加带颜色的消息

        Args:
            message: 消息文本
            color: CSS 颜色值
        """
        html = f'<span style="color: {color};">{self._escape_html(message)}</span>'
        self.output.insertHtml(html)
        self.output.insertPlainText("\n")

        # 自动滚动
        scrollbar = self.output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @staticmethod
    def _escape_html(text: str) -> str:
        """转义 HTML 特殊字符"""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )
