"""
GUI 应用入口

PyQt6 启动器的主应用类。
负责初始化 Qt 应用、加载样式、创建主窗口。
"""

import sys
import os
from pathlib import Path

# 确保 src 在路径中
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.gui.main_window import MainWindow
from src.config_manager import ConfigManager
from src.i18n import I18nManager
from src.logger import setup_logging, get_logger
from src.__version__ import __title__, __version__

logger = get_logger("gui")


class Application:
    """
    启动器应用程序

    PyQt6 应用的顶层封装。
    """

    def __init__(self):
        """初始化 GUI 应用"""
        # 创建 Qt 应用
        self.app = QApplication(sys.argv)

        # 设置应用属性
        self.app.setApplicationName(__title__)
        self.app.setApplicationVersion(__version__)
        self.app.setOrganizationName("MS Comfy Studio Pro")

        # DPI 缩放
        self.app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        self.app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

        # 初始化子系统
        self._init_config()
        self._init_logging()
        self._init_i18n()
        self._apply_font()
        self._apply_styles()

        # 创建主窗口
        self.main_window = MainWindow()

    def _init_config(self):
        """初始化配置"""
        self.config = ConfigManager()

    def _init_logging(self):
        """初始化日志"""
        log_level = self.config.get("logging.level", "INFO")
        log_dir = self.config.get("paths.logs_dir", "data/logs")
        max_size = self.config.get("logging.max_size_mb", 10)
        backup_count = self.config.get("logging.backup_count", 5)
        console = self.config.get("logging.console_output", True)

        setup_logging(
            log_level=log_level,
            log_dir=log_dir,
            max_size_mb=max_size,
            backup_count=backup_count,
            console_output=console,
        )

    def _init_i18n(self):
        """初始化国际化"""
        locale = self.config.get("app.default_locale", "zh-CN")
        self.i18n = I18nManager()
        try:
            self.i18n.set_locale(locale)
        except ValueError:
            logger.warning(f"语言 {locale} 不可用，使用默认语言")

    def _apply_font(self):
        """应用默认字体"""
        font = QFont("Microsoft YaHei UI", 10)
        if not font.exactMatch():
            font = QFont("Segoe UI", 10)
        self.app.setFont(font)

    def _apply_styles(self):
        """应用 QSS 样式"""
        style_file = Path(__file__).parent / "styles.qss"
        if style_file.exists():
            with open(style_file, "r", encoding="utf-8") as f:
                self.app.setStyleSheet(f.read())

    def run(self) -> int:
        """运行应用"""
        self.main_window.show()
        logger.info("启动器面板已启动")
        return self.app.exec()


def main():
    """GUI 应用入口点"""
    app = Application()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
