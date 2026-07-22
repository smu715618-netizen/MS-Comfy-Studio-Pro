"""widgets/environment_page.py — 环境管理页面组件"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QTextEdit, QFrame, QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.logger import get_logger

logger = get_logger("gui.environment")


class EnvironmentPage(QWidget):
    """环境管理页面 — 显示 Python/Intel/ComfyUI/依赖状态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._auto_refresh = True
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ---- Python 环境 ----
        py_group = self._make_group("Python 环境")
        py_layout = QVBoxLayout(py_group)
        self._py_version_lbl = QLabel("版本: --")
        self._py_path_lbl = QLabel("路径: --")
        self._py_arch_lbl = QLabel("架构: --")
        self._py_venv_lbl = QLabel("虚拟环境: --")
        py_layout.addWidget(self._py_version_lbl)
        py_layout.addWidget(self._py_path_lbl)
        py_layout.addWidget(self._py_arch_lbl)
        py_layout.addWidget(self._py_venv_lbl)
        layout.addWidget(py_group)

        # ---- Intel 运行环境 ----
        intel_group = self._make_group("Intel 运行环境 (XPU)")
        intel_layout = QVBoxLayout(intel_group)
        self._intel_driver_lbl = QLabel("GPU驱动: 未检测")
        self._intel_oneapi_lbl = QLabel("OneAPI: 未检测")
        self._intel_ipex_lbl = QLabel("PyTorch-IPEX: 未检测")
        intel_layout.addWidget(self._intel_driver_lbl)
        intel_layout.addWidget(self._intel_oneapi_lbl)
        intel_layout.addWidget(self._intel_ipex_lbl)
        self._intel_issues_lbl = QTextEdit()
        self._intel_issues_lbl.setMaximumHeight(60)
        self._intel_issues_lbl.setStyleSheet("background:#2a1a1a; color:#f38ba8; border-radius:4px;")
        intel_layout.addWidget(self._intel_issues_lbl)
        layout.addWidget(intel_group)

        # ---- ComfyUI ----
        cu_group = self._make_group("ComfyUI")
        cu_layout = QVBoxLayout(cu_group)
        self._cu_status_lbl = QLabel("状态: --")
        self._cu_commit_lbl = QLabel("Commit: --")
        cu_layout.addWidget(self._cu_status_lbl)
        cu_layout.addWidget(self._cu_commit_lbl)
        self._cu_btn_update = QPushButton("更新 ComfyUI")
        self._cu_btn_update.setObjectName("primaryBtn")
        self._cu_btn_update.clicked.connect(self._on_update_comfyui)
        cu_layout.addWidget(self._cu_btn_update)
        layout.addWidget(cu_group)

        # ---- 依赖包 ----
        dep_group = self._make_group("依赖包")
        dep_layout = QVBoxLayout(dep_group)
        self._dep_status_lbl = QLabel("状态: --")
        dep_layout.addWidget(self._dep_status_lbl)
        self._dep_detail = QTextEdit()
        self._dep_detail.setMaximumHeight(80)
        self._dep_detail.setReadOnly(True)
        self._dep_detail.setStyleSheet("background:#1e1e2e; color:#cdd6f4; border-radius:4px; font-size:10px;")
        dep_layout.addWidget(self._dep_detail)
        layout.addWidget(dep_group)

        # 刷新按钮和定时器
        btn_row = QHBoxLayout()
        self._btn_refresh = QPushButton("↻ 刷新")
        self._btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(self._btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        self._toggle_auto_refresh(True)

    def refresh(self):
        try:
            from src.env_manager import EnvironmentManager
            from pathlib import Path
            mgr = EnvironmentManager(str(Path(__file__).parent.parent.parent))
            self._data = mgr.get_full_status()
            self._render(self._data)
        except Exception as e:
            self._set_error(f"环境检测失败: {e}")

    def _render(self, d: dict):
        py = d.get("python", {})
        intel = d.get("intel", {})
        cu = d.get("comfyui", {})
        deps = d.get("dependencies", {})

        self._py_version_lbl.setText(f"版本: {py.get('version', '--')}")
        self._py_path_lbl.setText(f"路径: {py.get('path', '--')}")
        self._py_arch_lbl.setText(f"架构: {'64-bit' if py.get('is_64bit') else '32-bit'}")
        self._py_venv_lbl.setText(f"虚拟环境: {'已激活 ✓' if py.get('virtualenv') else '未激活 ✗'}")

        driver = intel.get("driver_available", False)
        drv_text = "✓ 可用" if driver else "✗ 未检测到"
        self._intel_driver_lbl.setText(f"GPU驱动: {drv_text} (版本: {intel.get('driver_version', '?')})")
        if driver:
            self._intel_driver_lbl.setStyleSheet("color:#a6e3a1")
        else:
            self._intel_driver_lbl.setStyleSheet("color:#f38ba8")

        oneapi_val = intel.get("oneapi_installed", False)
        oneapi_text = "✓ 已安装" if oneapi_val else "未安装（可选）"
        self._intel_oneapi_lbl.setText(f"OneAPI: {oneapi_text}")

        ipex_val = intel.get("ipex_available", False)
        if ipex_val:
            self._intel_ipex_lbl.setText(f"PyTorch-IPEX: ✓ 可用")
        else:
            self._intel_ipex_lbl.setText("PyTorch-IPEX: 未检测到")

        issues = intel.get("issues", [])
        self._intel_issues_lbl.setText(
            "<br>".join([f"⚠ {i}" for i in issues]) or "无问题"
        )

        cu_status = cu.get("installed", False) and cu.get("main_py_exists", False)
        self._cu_status_lbl.setText(f"状态: {'已安装 ✓' if cu_status else '未安装'}")
        if cu_status:
            self._cu_status_lbl.setStyleSheet("color:#a6e3a1")
        else:
            self._cu_status_lbl.setStyleSheet("color:#f9e2af")
        last = cu.get("last_commit", "?")
        branch = cu.get("branch", "?")
        self._cu_commit_lbl.setText(f"最近提交: {last} ({branch})")

        missing = deps.get("missing", [])
        self._dep_status_lbl.setText(f"缺失包: {len(missing)}")
        if missing:
            self._dep_status_lbl.setStyleSheet("color:#f38ba8")
        else:
            self._dep_status_lbl.setStyleSheet("color:#a6e3a1")
        self._dep_detail.setText(", ".join(missing) if missing else "所有必需包已安装 ✓")

    def _set_error(self, msg: str):
        self._intel_issues_lbl.setText(msg)

    def _on_update_comfyui(self):
        try:
            from src.env_manager import ComfyUIManager
            from pathlib import Path
            result = ComfyUIManager.update(str(Path(__file__).parent.parent.parent))
            self.refresh()
            logger.info(f"ComfyUI 更新: {'成功' if result else '失败'}")
        except Exception as e:
            logger.error(f"ComfyUI 更新失败: {e}")

    def _toggle_auto_refresh(self, enable: bool):
        if enable and not self._refresh_timer.isActive():
            self._refresh_timer.start(15000)  # 每15秒
        elif not enable:
            self._refresh_timer.stop()

    @staticmethod
    def _make_group(title: str) -> QGroupBox:
        g = QGroupBox(title)
        g.setStyleSheet("""
            QGroupBox {
                font-weight: bold; color: #89b4fa;
                border: 1px solid #313244; border-radius: 6px; padding-top: 12px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
        """)
        return g
