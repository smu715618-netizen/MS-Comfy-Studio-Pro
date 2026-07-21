"""
主窗口

启动器面板的主窗口。
包含侧边栏导航和主内容区域。
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QFrame, QLabel, QPushButton,
    QToolBar, QStatusBar, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction

from src.__version__ import __title__, __version__


class MainWindow(QMainWindow):
    """
    主窗口类

    启动器面板的主界面。
    包含：
    - 顶部工具栏
    - 左侧导航栏
    - 中间内容区域（堆叠）
    - 底部状态栏
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__title__} v{__version__}")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)

        # 初始化 UI
        self._init_ui()

    def _init_ui(self):
        """初始化用户界面"""
        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        self._init_toolbar(toolbar)

        # 主体布局
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 侧边导航
        self.nav_frame = self._create_nav_frame()
        body_layout.addWidget(self.nav_frame)

        # 内容区域
        self.content_stack = QStackedWidget()
        self._init_content_pages()
        body_layout.addWidget(self.content_stack)

        main_layout.addWidget(toolbar)
        main_layout.addLayout(body_layout)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _init_toolbar(self, toolbar):
        """初始化工具栏按钮"""
        # 启动 ComfyUI
        self.btn_start = QAction("▶ 启动 ComfyUI", self)
        self.btn_start.setToolTip("启动 ComfyUI 服务")
        self.btn_start.triggered.connect(self._on_start_comfy)
        toolbar.addAction(self.btn_start)

        # 停止 ComfyUI
        self.btn_stop = QAction("■ 停止", self)
        self.btn_stop.setToolTip("停止 ComfyUI 服务")
        self.btn_stop.setEnabled(False)
        self.btn_stop.triggered.connect(self._on_stop_comfy)
        toolbar.addAction(self.btn_stop)

        toolbar.addSeparator()

        # 刷新
        self.btn_refresh = QAction("↻ 刷新", self)
        self.btn_refresh.setToolTip("刷新系统状态")
        self.btn_refresh.triggered.connect(self._on_refresh)
        toolbar.addAction(self.btn_refresh)

        toolbar.addSeparator()

        # 设置
        self.btn_settings = QAction("⚙️ 设置", self)
        self.btn_settings.setToolTip("打开设置")
        self.btn_settings.triggered.connect(self._on_settings)
        toolbar.addAction(self.btn_settings)

        # 帮助
        self.btn_help = QAction("ℹ️ 帮助", self)
        self.btn_help.setToolTip("查看帮助")
        self.btn_help.triggered.connect(self._on_help)
        toolbar.addAction(self.btn_help)

    def _create_nav_frame(self) -> QFrame:
        """创建侧边导航栏"""
        nav = QFrame()
        nav.setFixedWidth(180)
        nav.setObjectName("navFrame")
        nav.setStyleSheet("""
            QFrame#navFrame {
                background-color: #1e1e2e;
                border-right: 1px solid #313244;
            }
            QFrame#navFrame QPushButton {
                text-align: left;
                padding: 10px 15px;
                border: none;
                border-radius: 5px;
                margin: 2px 8px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QFrame#navFrame QPushButton:hover {
                background-color: #313244;
            }
            QFrame#navFrame QPushButton:checked {
                background-color: #89b4fa;
                color: #1e1e2e;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(nav)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(4)

        # 导航按钮
        nav_items = [
            ("📊 概览", "overview"),
            ("💻 环境", "environment"),
            ("💾 GPU", "gpu"),
            ("📦 模型", "models"),
            ("🧱️ 节点", "nodes"),
            ("📚 工作流", "workflows"),
            ("🖥️ 插件", "plugins"),
            ("🔄 更新", "updates"),
            ("➕ 健康检查", "health"),
        ]

        self.nav_buttons = {}
        for text, page_id in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, pid=page_id: self._switch_page(pid))
            layout.addWidget(btn)
            self.nav_buttons[page_id] = btn

        # 默认选中概览
        self.nav_buttons["overview"].setChecked(True)

        layout.addStretch()
        return nav

    def _init_content_pages(self):
        """初始化内容页面（占位）"""
        # 概览页
        overview = self._create_placeholder_page("概览", "欢迎使用 MS Comfy Studio Pro")
        self.content_stack.addWidget(overview)

        # 其他页面（占位）
        for page_id in ["environment", "gpu", "models", "nodes", "workflows", "plugins", "updates", "health"]:
            page = self._create_placeholder_page(page_id, f"{page_id} 管理")
            self.content_stack.addWidget(page)

    def _create_placeholder_page(self, title: str, subtitle: str) -> QWidget:
        """创建占位页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(f"⭐ {title}")
        label.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        sub = QLabel(subtitle)
        sub.setStyleSheet("color: #6c7086; font-size: 14px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        hint = QLabel("此功能将在后续开发中实现")
        hint.setStyleSheet("color: #a6adc8; font-size: 12px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        return widget

    def _switch_page(self, page_id: str):
        """切换到指定页面"""
        index_map = {
            "overview": 0, "environment": 1, "gpu": 2, "models": 3,
            "nodes": 4, "workflows": 5, "plugins": 6, "updates": 7, "health": 8,
        }
        idx = index_map.get(page_id, 0)
        self.content_stack.setCurrentIndex(idx)

    def _on_start_comfy(self):
        """启动 ComfyUI"""
        self.status_bar.showMessage("正在启动 ComfyUI...")

    def _on_stop_comfy(self):
        """停止 ComfyUI"""
        self.status_bar.showMessage("正在停止 ComfyUI...")

    def _on_refresh(self):
        """刷新状态"""
        self.status_bar.showMessage("已刷新")

    def _on_settings(self):
        """打开设置"""
        QMessageBox.information(self, "设置", "设置功能即将推出")

    def _on_help(self):
        """帮助"""
        QMessageBox.information(
            self, "帮助",
            f"{__title__} v{__version__}\n\n"
            "专为 Intel Arc A750 (8GB) 优化的企业级 ComfyUI 平台。\n\n"
            "使用方法：\n"
            "1. 点击 '启动 ComfyUI' 开始使用\n"
            "2. 在左侧导航中管理模型、节点和工作流\n"
            "3. 使用 '健康检查' 监控系统状态",
        )
