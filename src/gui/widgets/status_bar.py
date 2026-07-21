"""
自定义状态栏

显示系统状态指示器和快速操作按钮。
"""

from PyQt6.QtWidgets import QStatusBar, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from src.logger import get_logger

logger = get_logger("gui.status_bar")


class CustomStatusBar(QStatusBar):
    """
    自定义状态栏

    包含：
    - 左侧：状态消息
    - 中间：进度条（可选）
    - 右侧：GPU 状态指示器
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("customStatusBar")
        self.setStyleSheet("""
            QStatusBar {
                background-color: #181825;
                border-top: 1px solid #313244;
                color: #a6adc8;
                font-size: 11px;
            }
        """)

        # 左侧状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.addWidget(self.status_label, 1)

        # 中间进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 3px;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        self.addPermanentWidget(self.progress_bar)

        # 右侧 GPU 状态
        self.gpu_label = QLabel("GPU: 检测中...")
        self.gpu_label.setObjectName("gpuLabel")
        self.gpu_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.addPermanentWidget(self.gpu_label)

        # 右侧版本
        self.version_label = QLabel("v0.1.0")
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.addPermanentWidget(self.version_label)

    def set_status(self, message: str, level: str = "info"):
        """
        设置状态消息

        Args:
            message: 状态消息
            level: 状态级别 (info/warning/error)
        """
        self.status_label.setText(message)

        colors = {
            "info": "#a6e3a1",
            "warning": "#f9e2af",
            "error": "#f38ba8",
        }
        color = colors.get(level, "#a6e3a1")
        self.status_label.setStyleSheet(f"color: {color};")

    def set_progress(self, value: int, maximum: int = 100):
        """设置进度条"""
        self.progress_bar.show()
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
        if value >= maximum:
            self.progress_bar.hide()

    def set_gpu_status(self, gpu_name: str):
        """设置 GPU 状态显示"""
        self.gpu_label.setText(f"GPU: {gpu_name}")

    def hide_progress(self):
        """隐藏进度条"""
        self.progress_bar.hide()
