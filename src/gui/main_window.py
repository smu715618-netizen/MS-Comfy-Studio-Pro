"""
主窗口 — Launcher GUI

启动器面板的主界面，连接 src.launcher.Launcher 提供：
- 首页 Dashboard（GPU/CPU/内存/ComfyUI 状态卡片）
- 实时日志面板
- 启动/停止 ComfyUI 按钮
- 健康检查

不加载 ComfyUI、模型、节点等模块（按需加载）。
只加载 launcher + 必需的 Qt。
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QFrame, QLabel, QPushButton,
    QToolBar, QStatusBar, QMessageBox, QTabWidget,
    QGroupBox, QGridLayout, QTextEdit, QProgressBar,
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont

from src.__version__ import __title__, __version__
from src.launcher import Launcher, LauncherState

# ── 字体 ──────────────────────────────────────
_FONT_FAMILY = "Microsoft YaHei UI" if Qt.fonts().isFontAvailable("Microsoft YaHei UI") else "Segoe UI"


class MainWindow(QMainWindow):
    """主窗口 — Launcher 控制面板"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__title__} v{__version__}")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)

        # 核心：启动器实例（延迟初始化，首次需要时才创建）
        self._launcher: Launcher | None = None
        self._dashboard_timer: QTimer | None = None

        self._init_ui()

    # ── UI 构建 ──────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 工具栏 ----
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(toolbar)
        self._toolbar_init(toolbar)

        # ---- 主体 ----
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # 左侧导航
        nav = self._nav_frame()
        body.addWidget(nav)

        # 右侧内容
        self.content_stack = QStackedWidget()
        self._build_pages()
        body.addWidget(self.content_stack)

        layout.addLayout(body)

        # 底部状态栏
        self.status_bar = self._status_bar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 — 点击「刷新」或 「启动 ComfyUI」开始")

    # ── 工具栏 ───────────────────────────────

    def _toolbar_init(self, toolbar):
        self._btn_start = QAction("▶ 启动", self)
        self._btn_start.setToolTip("启动 ComfyUI（自动检测硬件配置）")
        self._btn_start.triggered.connect(self._on_start)
        toolbar.addAction(self._btn_start)

        self._btn_stop = QAction("■ 停止", self)
        self._btn_stop.setToolTip("停止 ComfyUI")
        self._btn_stop.setEnabled(False)
        self._btn_stop.triggered.connect(self._on_stop)
        toolbar.addAction(self._btn_stop)

        toolbar.addSeparator()

        self._btn_refresh = QAction("↻ 刷新", self)
        self._btn_refresh.setToolTip("刷新仪表盘数据")
        self._btn_refresh.triggered.connect(self._on_refresh)
        toolbar.addAction(self._btn_refresh)

        toolbar.addSeparator()

        self._btn_health = QAction("🏥 健康", self)
        self._btn_health.setToolTip("运行系统健康检查")
        self._btn_health.triggered.connect(self._on_health)
        toolbar.addAction(self._btn_health)

    # ── 侧边导航 ─────────────────────────────

    def _nav_frame(self) -> QFrame:
        nav = QFrame()
        nav.setFixedWidth(160)
        nav.setStyleSheet("""
            QFrame { background-color:#181825; border-right:1px solid #313244; }
            QFrame QPushButton {
                text-align:left; padding:9px 12px; border:none; border-radius:4px;
                margin:2px 8px; color:#cdd6f4; font-size:13px;
                background-color:transparent;
            }
            QFrame QPushButton:hover { background-color:#313244; }
            QFrame QPushButton:checked { background-color:#89b4fa; color:#1e1e2e; font-weight:bold; }
        """)
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(6, 14, 6, 6)
        layout.setSpacing(3)

        self._nav_map: dict[str, QPushButton] = {}
        for text, page in [("📊 概览", "overview"), ("📝 日志", "log")]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, p=page: self._switch_page(p))
            layout.addWidget(btn)
            self._nav_map[page] = btn

        self._nav_map["overview"].setChecked(True)
        layout.addStretch()
        return nav

    # ── 页面构建 ─────────────────────────────

    def _build_pages(self):
        self.content_stack.addWidget(self._page_overview())   # 0
        self.content_stack.addWidget(self._page_log())         # 1

    def _switch_page(self, page: str):
        idx = {"overview": 0, "log": 1}.get(page, 0)
        self.content_stack.setCurrentIndex(idx)

    # ── Dashboard: 概览页 ───────────────────

    def _page_overview(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # 标题
        title = QLabel("欢迎使用 MS Comfy Studio Pro")
        title.setFont(QFont(_FONT_FAMILY, 16, QFont.Weight.Bold))
        title.setStyleSheet("color:#89b4fa;")
        lay.addWidget(title)

        subtitle = QLabel(f"专为 Intel Arc A750（8GB VRAM）优化 · v{__version__}")
        subtitle.setStyleSheet("color:#a6adc8;")
        lay.addWidget(subtitle)
        lay.addSpacing(8)

        # 四个状态卡片
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(12)

        card_names = [
            ("GPU", "未检测"),
            ("系统内存", "—"),
            ("Python", "—"),
            ("ComfyUI", "未安装"),
        ]
        self._card_labels: dict[str, QLabel] = {}
        for i, (name, val) in enumerate(card_names):
            grp = QGroupBox(name)
            txt = QLabel(val)
            txt.setStyleSheet("""
                QLabel {
                    color:#cdd6f4; font-size:14px; font-weight:bold;
                    background:#1e1e2e; border-radius:6px; padding:12px;
                    qproperty-alignment: AlignCenter;
                }
            """)
            inner = QVBoxLayout(grp)
            inner.setAlignment(txt, Qt.AlignmentFlag.AlignCenter)
            inner.setContentsMargins(8, 8, 8, 8)
            cards_layout.addWidget(grp, i // 2, i % 2)
            self._card_labels[name] = txt

        lay.addLayout(cards_layout)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_start = QPushButton("▶ 启动 ComfyUI")
        btn_start.setObjectName("primaryBtn")
        btn_start.setStyleSheet("""
            QPushButton#primaryBtn {
                background-color:#89b4fa; color:#1e1e2e; font-weight:bold;
                padding:10px 28px; border-radius:6px; font-size:14px;
            }
            QPushButton#primaryBtn:hover { background-color:#74c7ec; }
            QPushButton#primaryBtn:disabled { background-color:#585b70; color:#a6adc8; }
        """)
        btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(btn_start)

        btn_stop = QPushButton("■ 停止 ComfyUI")
        btn_stop.setObjectName("dangerBtn")
        btn_stop.setEnabled(False)
        btn_stop.setStyleSheet("""
            QPushButton#dangerBtn {
                background-color:#f38ba8; color:#1e1e2e; font-weight:bold;
                padding:10px 28px; border-radius:6px; font-size:14px;
            }
            QPushButton#dangerBtn:hover { background-color:#eba0ac; }
            QPushButton#dangerBtn:disabled { background-color:#45475a; color:#6c7086; }
        """)
        btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(btn_stop)
        btn_row.addStretch()
        self._btn_stop_widget = btn_stop
        lay.addLayout(btn_row)

        # 推荐配置
        rec = QGroupBox("硬件识别与推荐")
        rec_txt = QLabel("点击「刷新」获取详细信息…")
        rec_txt.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        rec_txt.setWordWrap(True)
        inner_rec = QVBoxLayout(rec)
        inner_rec.addWidget(rec_txt)
        lay.addWidget(rec)
        self._rec_label = rec_txt

        # 初始加载
        self._refresh_dashboard()

        return w

    # ── 日志页 ───────────────────────────────

    def _page_log(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel("Launcher 运行日志")
        lbl.setStyleSheet("font-weight:bold; color:#89b4fa; font-size:14px;")
        lay.addWidget(lbl)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 10))
        self._log_text.setStyleSheet("""
            QTextEdit {
                background:#181825; color:#cdd6f4; border:1px solid #313244;
                border-radius:4px; padding:8px;
            }
        """)
        lay.addWidget(self._log_text)

        btn_row = QHBoxLayout()
        btn_clear = QPushButton("清空日志")
        btn_clear.clicked.connect(self._log_text.clear)
        btn_copy = QPushButton("复制")
        btn_copy.clicked.connect(lambda: self._log_text.copy())
        btn_row.addWidget(btn_clear)
        btn_row.addWidget(btn_copy)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        return w

    # ── 状态栏 ───────────────────────────────

    def _status_bar(self) -> QStatusBar:
        sb = QStatusBar()
        self._sb_gpu = QLabel("GPU: --")
        self._sb_version = QLabel(__version__)
        sb.addWidget(self._sb_gpu, 1)
        sb.addPermanentWidget(self._sb_version)
        return sb

    # ── 操作 ─────────────────────────────────

    def _ensure_launcher(self):
        if self._launcher is None:
            from pathlib import Path
            project_root = str(Path(__file__).parent.parent.parent)
            self._launcher = Launcher(project_root)
            # 回调：更新日志页
            self._launcher.on_log_message(self._log_text.append)
        return self._launcher

    def _on_start(self):
        if self._launcher and self._launcher.state == LauncherState.STATE_RUNNING:
            return
        self._ensure_launcher()
        self._log_text.append("[INFO] 正在启动 ComfyUI...")
        ok = self._launcher.start_comfyui()
        self._update_state(ok)
        if ok:
            self._start_auto_refresh()
        else:
            self._log_text.append("[ERROR] 启动失败，请检查健康检查")

    def _on_stop(self):
        if not self._launcher:
            return
        self._log_text.append("[INFO] 正在停止 ComfyUI...")
        ok = self._launcher.stop_comfyui()
        self._update_state(ok)
        if ok:
            self._stop_auto_refresh()
            self._log_text.append("[INFO] ComfyUI 已停止")

    def _on_refresh(self):
        self._refresh_dashboard()

    def _on_health(self):
        self._ensure_launcher()
        self._log_text.append("[INFO] 运行健康检查...")
        result = self._launcher.health_check()
        overall = result.get("overall", "?")
        self._log_text.append(f"[{overall.upper()}] 健康检查完成")
        for k, v in result.get("details", {}).items():
            msg = v.get("message", "")
            self._log_text.append(f"  {k}: {msg}")

    def _update_state(self, started: bool):
        st = self._launcher.state if self._launcher else LauncherState.STATE_IDLE
        self._btn_start.setEnabled(st != LauncherState.STATE_RUNNING and st != LauncherState.STATE_CHECKING)
        self._btn_stop.setEnabled(st == LauncherState.STATE_RUNNING)
        self.status_bar.showMessage(f"状态: {st}")

    # ── 自动刷新 ─────────────────────────────

    def _start_auto_refresh(self):
        if self._dashboard_timer is not None:
            return
        self._dashboard_timer = QTimer(self)
        self._dashboard_timer.timeout.connect(self._refresh_dashboard)
        self._dashboard_timer.start(5000)  # 每 5 秒

    def _stop_auto_refresh(self):
        if self._dashboard_timer:
            self._dashboard_timer.stop()
            self._dashboard_timer = None

    def _refresh_dashboard(self):
        self._ensure_launcher()
        data = self._launcher.get_dashboard_data()

        gpu = data.get("gpu", {})
        sysd = data.get("system", {})
        comfy = data.get("comfyui", {})
        health = data.get("health", {})

        # 更新卡片
        self._safe_set(self._card_labels.get("GPU"),
                       f"{gpu.get('name','?')} ({gpu.get('memory_mb','?')}MB)")
        self._safe_set(self._card_labels.get("系统内存"),
                       f"{sysd.get('available_memory_mb','?')} / {sysd.get('total_memory_mb','?')} MB")
        self._safe_set(self._card_labels.get("Python"), sysd.get("python_version", "—"))
        self._safe_set(self._card_labels.get("ComfyUI"),
                       "运行中" if comfy.get("running") else
                       "已安装" if comfy.get("installed") else "未安装")

        # GPU 状态栏
        self.status_bar.setStatusTip("")
        gpu_type = gpu.get("type", "--")
        self._sb_gpu.setText(f"GPU: {gpu_name} ({gpu_mem}MB)")
        self._sb_gpu.setText(f"GPU: {gpu_type}")

        # 推荐
        rec_lines = []
        rec_lines.append(f"**GPU**: {gpu.get('name','?')} [{gpu.get('type','?')}]")
        if gpu.get("xpu_available"):
            rec_lines.append("- Intel XPU 可用 → 将作为首选后端")
        elif gpu.get("directml_available"):
            rec_lines.append("- DirectML 可用 → 将作为兼容兜底")
        elif gpu.get("cuda_available"):
            rec_lines.append("- CUDA 可用 → 将使用 NVIDIA 加速")
        else:
            rec_lines.append("- 未检测到 GPU → 仅使用 CPU")

        mem = sysd.get("total_memory_mb", 0)
        if mem < 16384:
            rec_lines.append(f"- 内存 {mem}MB < 16GB，建议升级至 16GB+")
        else:
            rec_lines.append(f"- 内存充足: {mem}MB")

        rec_lines.append(f"- Python {sysd.get('python_version','?')}")
        rec_lines.append(f"- ComfyUI: {'已安装' if comfy.get('installed') else '需先安装'}")

        state = self._launcher.state if self._launcher else LauncherState.IDLE
        if state == LauncherState.RUNNING:
            rec_lines.append("\n🟢 ComfyUI 正在运行")
        elif state == LauncherState.STARTING:
            rec_lines.append("\n🟡 正在启动…")
        elif state == LauncherState.ERROR:
            rec_lines.append("\n🔴 发生错误，请查看日志")

        self._rec_label.setText("\n".join(rec_lines))

        # 自动切换到概览页（如果当前在日志页且刚启动）
        # （不强制切换，由用户决定）

        # 更新按钮状态
        running = self._launcher and self._launcher.is_running()
        busy = self._launcher and self._launcher.is_busy()
        self._btn_start.setEnabled(not busy)
        self._btn_stop_widget.setEnabled(running)

    @staticmethod
    def _safe_set(label, text: str):
        if label is not None:
            label.setText(text)
