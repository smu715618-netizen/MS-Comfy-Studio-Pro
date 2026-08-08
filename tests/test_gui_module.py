"""
GUI 模块测试

测试启动器 GUI 层（不依赖 Qt 运行环境）。
通过 mock 模拟 Qt 组件，确保模块导入和逻辑正确。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── mock PyQt6 ─────────────────────────────────────────────
# 避免在没有 PyQt6 的环境中崩溃


class _MockObject:
    """通用 mock 对象，允许任意属性访问"""

    def __init__(self, *args, **kwargs):
        self._children = []
        for k, v in zip(args, kwargs.values()):
            if isinstance(k, str):
                setattr(self, k, v)
        self._kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return _MockObject(*args, **kwargs)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._children.append((name, value))

    def __getattr__(self, name):
        return _MockObject()


def _install_qt_mocks():
    """安装 PyQt6 mock 模块"""
    modules = {
        "PyQt6.QtWidgets": ["QWidget", "QMainWindow", "QVBoxLayout", "QHBoxLayout",
                            "QGridLayout", "QStackedWidget", "QFrame", "QLabel",
                            "QPushButton", "QToolBar", "QStatusBar", "QMessageBox",
                            "QTabWidget", "QGroupBox", "QTextEdit", "QProgressBar",
                            "QLineEdit", "QSpinBox", "QCheckBox", "QListWidget",
                            "QListWidgetItem", "QComboBox"],
        "PyQt6.QtCore": ["Qt", "QTimer", "QUrl", "pyqtSignal"],
        "PyQt6.QtGui": ["QFont", "QAction", "QColor", "QDesktopServices"],
        "PyQt6": ["Qt"],
    }
    for mod_name, classes in modules.items():
        if mod_name not in sys.modules:
            mod = type(sys)(mod_name)
            for cls_name in classes:
                setattr(mod, cls_name, _MockObject)
            sys.modules[mod_name] = mod


_install_qt_mocks()

# ── 测试 ───────────────────────────────────────────────────


class TestMainWindowImport:
    """测试 MainWindow 模块导入"""

    def test_main_window_imports(self):
        from src.gui.main_window import MainWindow
        assert MainWindow is not None

    def test_qaction_imported(self):
        """QAction 必须在正确的位置导入"""
        import ast
        with open(Path(__file__).parent.parent / "src" / "gui" / "main_window.py",
                  encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "PyQt6" in node.module:
                    for alias in node.names:
                        imports.append(alias.name)
        assert "QAction" in imports, "QAction 未导入 — 会导致运行时崩溃"

    def test_console_widget_used_in_log_page(self):
        """日志页应使用 ConsoleWidget"""
        with open(Path(__file__).parent.parent / "src" / "gui" / "main_window.py",
                  encoding="utf-8") as f:
            content = f.read()
        assert "ConsoleWidget" in content, "日志页未集成 ConsoleWidget"

    def test_no_launcher_state_idle_bug(self):
        """不能有 LauncherState.IDLE 错误引用"""
        with open(Path(__file__).parent.parent / "src" / "gui" / "main_window.py",
                  encoding="utf-8") as f:
            content = f.read()
        # LauncherState.IDLE（无 STATE_）是 bug，只有 STATE_IDLE 正确
        assert "LauncherState.IDLE" not in content, \
            "发现 LauncherState.IDLE bug — 应使用 LauncherState.STATE_IDLE"

    def test_port_spinbox_present(self):
        """端口配置 QSpinBox 必须存在"""
        with open(Path(__file__).parent.parent / "src" / "gui" / "main_window.py",
                  encoding="utf-8") as f:
            content = f.read()
        assert "_port_spin" in content, "端口配置组件缺失"

    def test_environment_page_in_nav(self):
        """导航应包含环境页"""
        with open(Path(__file__).parent.parent / "src" / "gui" / "main_window.py",
                  encoding="utf-8") as f:
            content = f.read()
        assert "environment" in content, "环境页未加入导航"
        assert "EnvironmentPage" in content, "EnvironmentPage 未集成"

    def test_open_browser_action(self):
        """应有打开浏览器功能"""
        with open(Path(__file__).parent.parent / "src" / "gui" / "main_window.py",
                  encoding="utf-8") as f:
            content = f.read()
        assert "_on_open_browser" in content, "打开浏览器方法缺失"
        assert "QDesktopServices" in content, "QDesktopServices 未导入"


class TestLauncherState:
    """测试 LauncherState 状态常量"""

    def test_all_states_defined(self):
        from src.launcher import LauncherState
        assert hasattr(LauncherState, "STATE_IDLE")
        assert hasattr(LauncherState, "STATE_CHECKING")
        assert hasattr(LauncherState, "STATE_STARTING")
        assert hasattr(LauncherState, "STATE_RUNNING")
        assert hasattr(LauncherState, "STATE_STOPPING")
        assert hasattr(LauncherState, "STATE_ERROR")

    def test_state_values(self):
        from src.launcher import LauncherState
        assert LauncherState.STATE_IDLE == "idle"
        assert LauncherState.STATE_RUNNING == "running"
        assert LauncherState.STATE_STARTING == "starting"

    def test_property_access(self):
        from src.launcher import LauncherState
        ls = LauncherState()
        assert ls.state == "idle"
        assert ls.is_idle() is True
        assert ls.is_running() is False
        assert ls.is_busy() is False

    def test_state_transitions(self):
        from src.launcher import LauncherState
        ls = LauncherState()
        ls.state = LauncherState.STATE_STARTING
        assert ls.state == "starting"
        assert ls.is_busy() is True
        ls.state = LauncherState.STATE_RUNNING
        assert ls.is_running() is True


class TestCapabilityFramework:
    """测试 AI Capability 框架"""

    def test_registry_singleton(self):
        from src.capability.base import CapabilityRegistry
        r1 = CapabilityRegistry.instance()
        r2 = CapabilityRegistry.instance()
        assert r1 is r2

    def test_executor_hub_singleton(self):
        from src.capability.base import ExecutorHub
        h1 = ExecutorHub.instance()
        h2 = ExecutorHub.instance()
        assert h1 is h2

    def test_capability_output_dataclass(self):
        from src.capability.base import CapabilityOutput
        out = CapabilityOutput(success=True, output_data={"result": 42})
        assert out.success is True
        assert out.output_data == {"result": 42}

    def test_capability_param_validation(self):
        from src.capability.base import CapabilityParam
        param = CapabilityParam("count", "int", required=True, min_val=1, max_val=10)
        ok, msg = param.validate(5)
        assert ok is True
        ok, msg = param.validate(None)
        assert ok is False
        ok, msg = param.validate(15)
        assert ok is False


class TestConfigManager:
    """测试配置管理器"""

    def test_config_manager_loads(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        assert cm is not None

    def test_config_get_nested(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        port = cm.get("comfyui.port")
        assert port == 8188

    def test_config_get_default(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        val = cm.get("nonexistent.key", "fallback")
        assert val == "fallback"

    def test_config_get_gpu_type(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        ptype = cm.get("gpu.preferred_type")
        assert ptype == "intel_xpu"


class TestConsoleWidgetLogic:
    """测试 ConsoleWidget 纯逻辑（不依赖 Qt 渲染）"""

    def test_console_widget_import(self):
        from src.gui.widgets.console_widget import ConsoleWidget
        assert ConsoleWidget is not None

    def test_console_escape_html(self):
        from src.gui.widgets.console_widget import ConsoleWidget
        assert ConsoleWidget._escape_html("<test>") == "&lt;test&gt;"
        assert ConsoleWidget._escape_html('a"b') == 'a&quot;b'
        assert ConsoleWidget._escape_html("x&y") == "x&amp;y"


class TestStylesQSS:
    """测试 styles.qss 存在性和基本格式"""

    def test_styles_file_exists(self):
        qss_path = Path(__file__).parent.parent / "src" / "gui" / "styles.qss"
        assert qss_path.exists(), "styles.qss 文件缺失"

    def test_styles_has_catppuccin_colors(self):
        qss_path = Path(__file__).parent.parent / "src" / "gui" / "styles.qss"
        content = qss_path.read_text(encoding="utf-8")
        # Catppuccin Mocha 特征色
        assert "#1e1e2e" in content, "缺少 Mocha 背景色 #1e1e2e"
        assert "#89b4fa" in content, "缺少 Mocha 蓝色 #89b4fa"
        assert "#cdd6f4" in content, "缺少 Mocha 文字色 #cdd6f4"
        assert "#181825" in content, "缺少 Mocha 深色背景 #181825"

    def test_styles_no_syntax_errors(self):
        """简单验证 QSS 括号匹配"""
        qss_path = Path(__file__).parent.parent / "src" / "gui" / "styles.qss"
        content = qss_path.read_text(encoding="utf-8")
        # 去掉注释
        clean = "".join(
            line for line in content.split("\n")
            if not line.strip().startswith("/*") and not line.strip().startswith("*")
        )
        assert clean.count("{") == clean.count("}"), "QSS 括号不匹配"


class TestEnvironmentPageImport:
    """测试环境页模块导入"""

    def test_environment_page_import(self):
        from src.gui.widgets.environment_page import EnvironmentPage
        assert EnvironmentPage is not None

    def test_log_panel_import(self):
        from src.gui.widgets.log_panel import LogPanel
        assert LogPanel is not None

    def test_status_bar_import(self):
        from src.gui.widgets.status_bar import CustomStatusBar
        assert CustomStatusBar is not None


class TestPortraitAPI:
    """测试 PortraitAPI 接口定义（不依赖推理引擎）"""

    def test_portrait_api_class_exists(self):
        from src.ai.portrait.api import PortraitAPI
        assert PortraitAPI is not None

    def test_portrait_api_has_all_methods(self):
        from src.ai.portrait.api import PortraitAPI
        required = ["face_detect", "portrait_segment", "upscale_face",
                    "remove_object", "expand_canvas", "inpaint_region", "do_all"]
        for method in required:
            assert hasattr(PortraitAPI, method), f"PortraitAPI 缺少方法: {method}"

    def test_capability_registry_has_execute(self):
        from src.capability.base import CapabilityRegistry
        assert hasattr(CapabilityRegistry, "execute") is False  # Registry 没有 execute，ExecutorHub 才有
        # 确认 execute 在 ExecutorHub 上
        from src.capability.base import ExecutorHub
        assert hasattr(ExecutorHub, "execute")


class TestPipelineEngine:
    """测试 Pipeline 引擎"""

    def test_pipeline_add_step(self):
        from src.capability.base import PipelineEngine
        pe = PipelineEngine()
        step_id = pe.add_step("fake_cap", {"x": 1})
        assert step_id.startswith("step_")
        assert len(pe._steps) == 1

    def test_pipeline_validate_order_empty(self):
        from src.capability.base import PipelineEngine
        pe = PipelineEngine()
        ok, errors = pe.validate_order()
        assert ok is True
        assert len(errors) == 0

    def test_pipeline_remove_step(self):
        from src.capability.base import PipelineEngine
        pe = PipelineEngine()
        pe.add_step("cap1", {})
        pe.add_step("cap2", {})
        assert pe.remove_step("step_1") is True
        assert len(pe._steps) == 1
        assert pe.remove_step("step_99") is False


class TestStartupConfig:
    """测试启动配置自动生成"""

    def test_startup_config_creation(self):
        from src.launcher import StartupConfig
        from src.config_manager import ConfigManager
        from src.gpu_detector import GPUInfo, GPUType
        cm = ConfigManager()
        gpu = GPUInfo(
            gpu_type=GPUType.INTEL_XPU,
            name="Test GPU",
            memory_total_mb=8192,
            xpu_supported=True,
            cuda_supported=False,
            directml_supported=False,
        )
        sc = StartupConfig(cm, gpu)
        assert sc.port == 8188
        assert sc.host == "127.0.0.1"
        args = sc.get_args()
        assert "--port" in args
        assert "8188" in args


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
