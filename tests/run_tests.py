"""
Full test suite runner — manual pytest replacement
All tests defined as functions for maximum compatibility.
"""
import sys
import tempfile
import logging
import shutil
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Import ConsoleWidget directly to avoid PyQt6 dependency in test env
import importlib.util
_cw_spec = importlib.util.spec_from_file_location(
    "console_widget",
    _PROJECT_ROOT / "src" / "gui" / "widgets" / "console_widget.py",
)
_cw_mod = importlib.util.module_from_spec(_cw_spec)
# Mock PyQt6 before executing
import types
_qt_names = ['QWidget', 'QMainWindow', 'QVBoxLayout', 'QHBoxLayout',
             'QGridLayout', 'QStackedWidget', 'QFrame', 'QLabel',
             'QPushButton', 'QToolBar', 'QStatusBar', 'QMessageBox',
             'QTabWidget', 'QGroupBox', 'QTextEdit', 'QProgressBar',
             'QLineEdit', 'QSpinBox', 'QCheckBox', 'QListWidget',
             'QListWidgetItem', 'QComboBox', 'Qt', 'QTimer', 'QUrl',
             'pyqtSignal', 'QFont', 'QAction', 'QColor', 'QDesktopServices']
_qt_mod = types.ModuleType('PyQt6.QtWidgets')
for n in _qt_names:
    setattr(_qt_mod, n, type(n, (), {}))
_sys_mod = types.ModuleType('PyQt6.QtCore')
for n in ['Qt', 'QTimer', 'QUrl', 'pyqtSignal']:
    setattr(_sys_mod, n, type(n, (), {}))
_gui_mod = types.ModuleType('PyQt6.QtGui')
for n in ['QFont', 'QAction', 'QColor', 'QDesktopServices']:
    setattr(_gui_mod, n, type(n, (), {}))
_qtcore_mod = types.ModuleType('PyQt6.QtCore')
setattr(_qtcore_mod, 'Qt', type('Qt', (), {}))
setattr(_qtcore_mod, 'QTimer', type('QTimer', (), {}))
setattr(_qtcore_mod, 'QUrl', type('QUrl', (), {}))
setattr(_qtcore_mod, 'pyqtSignal', lambda *a, **k: None)
_pyqt6_mod = types.ModuleType('PyQt6')
_pyqt6_mod.QtWidgets = _qt_mod
_pyqt6_mod.QtCore = _qtcore_mod
_pyqt6_mod.QtGui = _gui_mod
sys.modules['PyQt6'] = _pyqt6_mod
sys.modules['PyQt6.QtWidgets'] = _qt_mod
sys.modules['PyQt6.QtCore'] = _qtcore_mod
sys.modules['PyQt6.QtGui'] = _gui_mod
_cw_spec.loader.exec_module(_cw_mod)
ConsoleWidget = _cw_mod.ConsoleWidget

from src.models import (
    ModelManager, ModelType, ModelStatus, ModelMetadata,
    ModelScanner, ModelIndex, ModelVerifier,
)
from src.config_manager import ConfigManager
from src.capability.base import (
    CapabilityRegistry, ExecutorHub, CapabilityOutput,
    CapabilityParam, PipelineEngine,
)
from src.launcher import LauncherState, StartupConfig
from src.workflows.nodes import ParamInfo, ParamType, NodeSignature, NodeType, NodeRegistry
from src.workflows import signatures
from src.logger import setup_logging, get_logger, LoggerManager
from src.gpu_detector import GPUDetector, GPUInfo, GPUType
from src.i18n import I18nManager
from src.core.event_bus import EventBus, Event
from src.workflows.parser import Workflow, NodeInstance, Connection
from src.workflows.bindings import Binding, BindingEngine
from src.workflows import WorkflowManager
from src.health_check import HealthChecker
from src.nodes import NodeManager


results = {"passed": 0, "failed": 0, "errors": 0}
failures = []
errors = []


def run(name, func):
    try:
        func()
        results["passed"] += 1
        print(f"  PASS: {name}")
    except AssertionError as e:
        results["failed"] += 1
        failures.append((name, str(e)))
        print(f"  FAIL: {name}: {e}")
    except Exception as e:
        results["errors"] += 1
        errors.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ERROR: {name}: {type(e).__name__}: {e}")


def _mk_project():
    d = tempfile.mkdtemp()
    md = Path(d) / "data" / "models"
    md.mkdir(parents=True)
    for mt in ModelType:
        (md / mt.value).mkdir(exist_ok=True)
    return d


def _cleanup(d):
    shutil.rmtree(d, ignore_errors=True)


# ===== TestModelMetadata =====
def test_meta_serialization():
    m = ModelMetadata(name="test", model_type=ModelType.CHECKPOINT,
                      filename="t.safetensors", file_size_bytes=1234567)
    d = m.to_dict()
    r = ModelMetadata.from_dict(d)
    assert r.name == "test"
    assert r.model_type == ModelType.CHECKPOINT
    assert r.file_size_bytes == 1234567


def test_status_enum():
    m = ModelMetadata(name="t", model_type=ModelType.VAE, filename="t.pt")
    assert m.status == ModelStatus.AVAILABLE
    m.status = ModelStatus.VERIFYING
    assert m.status == ModelStatus.VERIFYING


def test_model_type_display():
    assert ModelType.CHECKPOINT.display_name == "Checkpoint"
    assert ModelType.LORA.display_name == "LoRA"


def test_model_type_formats():
    assert ".safetensors" in ModelType.CHECKPOINT.supported_formats
    assert ".ckpt" in ModelType.CHECKPOINT.supported_formats


# ===== TestModelIndex =====
def test_index_add_get():
    with tempfile.TemporaryDirectory() as d:
        idx = ModelIndex(Path(d) / "index.json")
        idx.add_or_update(ModelMetadata(name="x", model_type=ModelType.CHECKPOINT, filename="x.safetensors"))
        assert idx.get("x").name == "x"


def test_index_persistence():
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "index.json"
        ModelIndex(f).add_or_update(ModelMetadata(name="p", model_type=ModelType.LORA, filename="p.safetensors"))
        assert ModelIndex(f).get("p").name == "p"


def test_index_get_by_type():
    with tempfile.TemporaryDirectory() as d:
        idx = ModelIndex(Path(d) / "index.json")
        for i in range(3):
            idx.add_or_update(ModelMetadata(name=f"c{i}", model_type=ModelType.CHECKPOINT, filename=f"c{i}.safetensors"))
        idx.add_or_update(ModelMetadata(name="v1", model_type=ModelType.VAE, filename="v1.pt"))
        assert len(idx.get_by_type(ModelType.CHECKPOINT)) == 3
        assert len(idx.get_by_type(ModelType.VAE)) == 1


def test_index_remove():
    with tempfile.TemporaryDirectory() as d:
        idx = ModelIndex(Path(d) / "index.json")
        idx.add_or_update(ModelMetadata(name="r", model_type=ModelType.VAE, filename="r.pt"))
        assert idx.remove("r") is True
        assert idx.get("r") is None
        assert idx.remove("r") is False


def test_index_count_by_type():
    with tempfile.TemporaryDirectory() as d:
        idx = ModelIndex(Path(d) / "index.json")
        for i in range(2):
            idx.add_or_update(ModelMetadata(name=f"c{i}", model_type=ModelType.CHECKPOINT, filename=f"c{i}.safetensors"))
        assert idx.count_by_type().get("checkpoints", 0) == 2


def test_index_get_all():
    with tempfile.TemporaryDirectory() as d:
        idx = ModelIndex(Path(d) / "index.json")
        idx.add_or_update(ModelMetadata(name="a", model_type=ModelType.CHECKPOINT, filename="a.safetensors"))
        idx.add_or_update(ModelMetadata(name="b", model_type=ModelType.LORA, filename="b.safetensors"))
        assert len(idx.get_all()) == 2


# ===== TestModelManager =====
def test_mm_init():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        assert mm.model_root.exists()
    finally:
        _cleanup(d)


def test_mm_register():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        f = mm.model_root / "checkpoints" / "test.safetensors"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"data")
        meta = mm.register_model_file(f, ModelType.CHECKPOINT)
        assert meta is not None
        assert meta.name == "test"
    finally:
        _cleanup(d)


def test_mm_get():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        f = mm.model_root / "checkpoints" / "my_model.safetensors"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"data")
        mm.register_model_file(f, ModelType.CHECKPOINT)
        assert mm.get_model("my_model").name == "my_model"
    finally:
        _cleanup(d)


def test_mm_by_type():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        for i in range(3):
            f = mm.model_root / "checkpoints" / f"ckpt{i}.safetensors"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"data")
            mm.register_model_file(f, ModelType.CHECKPOINT)
        vf = mm.model_root / "vae" / "vae.pt"
        vf.parent.mkdir(parents=True, exist_ok=True)
        vf.write_bytes(b"data")
        mm.register_model_file(vf, ModelType.VAE)
        assert len(mm.get_models_by_type(ModelType.CHECKPOINT)) == 3
        assert len(mm.get_models_by_type(ModelType.VAE)) == 1
    finally:
        _cleanup(d)


def test_mm_counts():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        f = mm.model_root / "checkpoints" / "a.safetensors"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"data")
        mm.register_model_file(f, ModelType.CHECKPOINT)
        assert mm.get_model_counts().get("checkpoints", 0) == 1
    finally:
        _cleanup(d)


def test_mm_remove():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        f = mm.model_root / "checkpoints" / "rm.safetensors"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"data")
        mm.register_model_file(f, ModelType.CHECKPOINT)
        assert mm.remove_model_index("rm") is True
        assert mm.get_model("rm") is None
        assert mm.remove_model_index("rm") is False
    finally:
        _cleanup(d)


def test_mm_stats():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        stats = mm.get_storage_stats()
        assert "total_bytes" in stats
        assert "total_mb" in stats
        assert "file_count" in stats
        assert "indexed_count" in stats
        assert "type_counts" in stats
    finally:
        _cleanup(d)


def test_mm_persistence():
    d = _mk_project()
    try:
        mm1 = ModelManager(project_root=d)
        f = mm1.model_root / "checkpoints" / "persist.safetensors"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"data")
        mm1.register_model_file(f, ModelType.CHECKPOINT)
        mm2 = ModelManager(project_root=d)
        assert mm2.get_model("persist") is not None
    finally:
        _cleanup(d)


def test_mm_scan():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        f1 = mm.model_root / "checkpoints" / "scan1.safetensors"
        f1.parent.mkdir(parents=True, exist_ok=True)
        f1.write_bytes(b"data")
        f2 = mm.model_root / "vae" / "scan2.safetensors"
        f2.parent.mkdir(parents=True, exist_ok=True)
        f2.write_bytes(b"data")
        new = mm.scan_and_index(force=True)
        assert new >= 2
        names = {m.name for m in mm.get_all_models()}
        assert "scan1" in names
        assert "scan2" in names
    finally:
        _cleanup(d)


def test_mm_verify():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        f = mm.model_root / "checkpoints" / "verify.safetensors"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"data")
        meta = mm.register_model_file(f, ModelType.CHECKPOINT)
        assert meta.sha256_hash != ""
        assert mm.verify_model("verify") is True
    finally:
        _cleanup(d)


def test_mm_verify_missing():
    d = _mk_project()
    try:
        mm = ModelManager(project_root=d)
        f = mm.model_root / "checkpoints" / "miss.safetensors"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"data")
        mm.register_model_file(f, ModelType.CHECKPOINT)
        f.unlink()
        assert mm.verify_model("miss") is False
    finally:
        _cleanup(d)


# ===== TestModelScanner =====
def test_scan_empty():
    with tempfile.TemporaryDirectory() as d:
        assert ModelScanner(Path(d)).scan_by_type(ModelType.CHECKPOINT) == []


def test_scan_with_files():
    with tempfile.TemporaryDirectory() as d:
        md = Path(d)
        cd = md / "checkpoints"
        cd.mkdir()
        (cd / "m1.safetensors").write_bytes(b"d")
        (cd / "m2.ckpt").write_bytes(b"d")
        (cd / ".hidden").write_bytes(b"h")
        results = ModelScanner(md).scan_by_type(ModelType.CHECKPOINT)
        names = {r.name for r in results}
        assert "m1.safetensors" in names and "m2.ckpt" in names and ".hidden" not in names


def test_scan_nonexistent():
    with tempfile.TemporaryDirectory() as d:
        assert ModelScanner(Path(d)).scan_by_type(ModelType.IPADAPTER) == []


# ===== TestModelVerifier =====
def test_sha256():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello")
        f.flush()
        h = ModelVerifier.calculate_sha256(Path(f.name))
        assert h is not None and len(h) == 64
    os.unlink(f.name)


def test_verify_match():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test")
        f.flush()
        h = ModelVerifier.calculate_sha256(Path(f.name))
        assert ModelVerifier.verify(Path(f.name), h) is True
    os.unlink(f.name)


def test_verify_mismatch():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test")
        f.flush()
        assert ModelVerifier.verify(Path(f.name), "wrong") is False
    os.unlink(f.name)


# ===== TestConfigManager =====
def test_config_loads():
    assert ConfigManager() is not None


def test_config_nested():
    assert ConfigManager().get("comfyui.port") == 8188


def test_config_default():
    assert ConfigManager().get("no.key", "fb") == "fb"


def test_config_gpu():
    assert ConfigManager().get("gpu.preferred_type") == "intel_xpu"


# ===== TestCapability =====
def test_registry_singleton():
    assert CapabilityRegistry.instance() is CapabilityRegistry.instance()


def test_executor_singleton():
    assert ExecutorHub.instance() is ExecutorHub.instance()


def test_output():
    out = CapabilityOutput(success=True, output_data={"r": 42})
    assert out.success and out.output_data == {"r": 42}


def test_param_validate():
    p = CapabilityParam("count", "int", required=True, min_val=1, max_val=10)
    ok, _ = p.validate(5)
    assert ok
    assert not p.validate(None)[0]
    assert not p.validate(15)[0]


def test_pipeline_add():
    pe = PipelineEngine()
    sid = pe.add_step("c1", {"x": 1})
    assert sid.startswith("step_") and len(pe._steps) == 1


def test_pipeline_validate_empty():
    ok, errs = PipelineEngine().validate_order()
    assert ok and len(errs) == 0


def test_pipeline_remove():
    pe = PipelineEngine()
    pe.add_step("c1", {})
    assert pe.remove_step("step_1") is True
    assert pe.remove_step("step_99") is False


# ===== TestLauncherState =====
def test_states_exist():
    assert hasattr(LauncherState, "STATE_IDLE") and hasattr(LauncherState, "STATE_RUNNING")


def test_state_values():
    assert LauncherState.STATE_IDLE == "idle" and LauncherState.STATE_RUNNING == "running"


def test_state_property():
    ls = LauncherState()
    assert ls.state == "idle" and ls.is_idle() and not ls.is_running()


def test_state_transitions():
    ls = LauncherState()
    ls.state = LauncherState.STATE_STARTING
    assert ls.state == "starting" and ls.is_busy()
    ls.state = LauncherState.STATE_RUNNING
    assert ls.is_running()


# ===== TestParamInfo =====
def test_paraminfo_optional():
    p = ParamInfo(name="mask", param_type=ParamType.MASK, optional=True)
    assert p.optional is True
    d = p.to_dict()
    assert d["optional"] is True
    p2 = ParamInfo.from_dict(d)
    assert p2.optional is True


def test_paraminfo_default():
    p = ParamInfo(name="x", param_type=ParamType.INT)
    assert p.optional is False


# ===== TestSignatures =====
def test_signatures_load():
    sig = NodeRegistry.get("LoadImage")
    assert sig is not None
    mask = [p for p in sig.output_params if p.name == "mask"][0]
    assert mask.optional is True


def test_all_defined():
    for cls in ["CheckpointLoaderSimple", "KSampler", "CLIPTextEncode", "EmptyLatentImage",
                "VAEDecode", "SaveImage", "UpscaleImage", "ControlNetApply", "ImageScale", "LoadImage"]:
        assert NodeRegistry.has(cls), f"{cls} not registered"


# ===== TestLogger =====
def test_logger_singleton():
    assert LoggerManager() is LoggerManager()


def test_logger_level_debug():
    LoggerManager._instance = None
    d = tempfile.mkdtemp()
    try:
        setup_logging(log_level="DEBUG", log_dir=d, console_output=False)
        logger = get_logger("t_debug_test_v2")
        assert logger.level == logging.DEBUG
    finally:
        logging.getLogger().handlers.clear()
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def test_logger_level_warning():
    LoggerManager._instance = None
    d = tempfile.mkdtemp()
    try:
        setup_logging(log_level="WARNING", log_dir=d, console_output=False)
        logger = get_logger("t_warn_test_v2")
        assert logger.level == logging.WARNING
    finally:
        logging.getLogger().handlers.clear()
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def test_logger_name():
    LoggerManager._instance = None
    d = tempfile.mkdtemp()
    try:
        setup_logging(log_dir=d, console_output=False)
        assert get_logger("mod_name_test_v2").name == "mod_name_test_v2"
    finally:
        logging.getLogger().handlers.clear()
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# ===== TestStartupConfig =====
def test_startup_config():
    cm = ConfigManager()
    gpu = GPUInfo(gpu_type=GPUType.INTEL_XPU, name="A750", memory_total_mb=8192,
                  xpu_supported=True, cuda_supported=False, directml_supported=False)
    sc = StartupConfig(cm, gpu)
    assert sc.port == 8188 and sc.host == "127.0.0.1"
    args = sc.get_args()
    assert "--port" in args and "--xpu" in args


# ===== TestConsoleWidget =====
def test_console_escape():
    assert ConsoleWidget._escape_html("<test>") == "&lt;test&gt;"
    assert ConsoleWidget._escape_html("x&y") == "x&amp;y"


# ===== TestStylesQSS =====
def test_styles():
    qss = Path("src/gui/styles.qss")
    assert qss.exists()
    c = qss.read_text(encoding="utf-8")
    assert "#1e1e2e" in c and "#89b4fa" in c
    assert c.count("{") == c.count("}")


# ===== TestPortraitAPI =====
def test_portrait_methods():
    from src.ai.portrait.api import PortraitAPI
    for m in ["face_detect", "portrait_segment", "upscale_face",
              "remove_object", "expand_canvas", "inpaint_region", "do_all"]:
        assert hasattr(PortraitAPI, m)


# ===== TestWorkflowParser =====
def test_workflow_parse():
    wf = Workflow.from_json('{"name": "test", "nodes": {}, "connections": []}')
    assert wf.name == "test" and wf.node_ids == []


def test_workflow_to_json():
    assert "w1" in Workflow(name="w1").to_json()


def test_connection_rt():
    c = Connection("n1", 0, "n2", "p1", "image")
    c2 = Connection.from_dict(c.to_dict())
    assert c2.from_node == "n1" and c2.to_port == "p1"


# ===== TestBindingEngine =====
def test_binding_rt():
    b = Binding("n1", "p1", "value", value=42)
    b2 = Binding.from_dict(b.to_dict())
    assert b2.target_node == "n1" and b2.value == 42


def test_binding_engine():
    be = BindingEngine()
    be.add_binding(Binding("n1", "p1", "value", value=10))
    assert be.get_binding("n1", "p1") is not None
    assert be.get_control_value("x") is None


# ===== TestNodeSignature =====
def test_sig_create():
    sig = NodeSignature(node_class="Test", display_name="测试", node_type=NodeType.BUILTIN)
    assert sig.node_class == "Test" and len(sig.input_params) == 0


def test_sig_roundtrip():
    sig = NodeSignature(
        node_class="RT", display_name="往返", node_type=NodeType.BUILTIN,
        input_params=[ParamInfo(name="x", param_type=ParamType.INT, default=42)],
    )
    r = NodeSignature.from_dict(sig.to_dict())
    assert r.node_class == "RT" and r.input_params[0].default == 42


def test_registry():
    sig = NodeSignature(node_class="RegTest", display_name="注册")
    NodeRegistry.register(sig)
    assert NodeRegistry.has("RegTest")
    assert NodeRegistry.get("RegTest") is sig
    assert len(NodeRegistry.get_all()) > 0


# ===== TestEventBus =====
def test_event_publish():
    bus = EventBus()
    called = []
    bus.subscribe("system", "test", lambda e: called.append(e.data))
    bus.publish_simple("system", "test", {"x": 1})
    assert called == [{"x": 1}]


def test_event_once():
    bus = EventBus()
    count = [0]
    bus.subscribe("system", "once", lambda e: count.__setitem__(0, count[0] + 1), once=True)
    bus.publish_simple("system", "once", {})
    bus.publish_simple("system", "once", {})
    assert count[0] == 1


# ===== TestI18n =====
def test_i18n_load():
    assert I18nManager().t("app.name") == "MS Comfy Studio Pro"


def test_i18n_fallback():
    assert I18nManager().t("no.key", "default") == "default"


# ===== TestProjectStructure =====
def test_root_files():
    root = Path(__file__).parent
    for f in ["README.md", "LICENSE", "pyproject.toml", "requirements.txt",
              "setup.bat", "run_comfy.bat", "run_launcher.bat"]:
        assert (root.parent / f).exists()


def test_config_files():
    root = Path(__file__).parent
    for f in ["configs/default.yaml", "configs/xpu.yaml"]:
        assert (root.parent / f).exists()


def test_src_modules():
    root = Path(__file__).parent
    for f in ["src/launcher.py", "src/models.py", "src/nodes.py", "src/workflows.py",
              "src/gui/main_window.py", "src/gui/styles.qss"]:
        assert (root.parent / f).exists()


# ===== TestGPUDetector =====
def test_gpu_detect():
    d = GPUDetector()
    info = d.detect()
    assert info is not None
    assert info.gpu_type is not None


def test_gpu_no_crash_nvidia():
    info = GPUDetector()._detect_nvidia()
    assert info is not None
    assert info.gpu_type.value == "unknown" or info.name == ""


def test_gpu_system_info():
    info = GPUDetector().get_system_info()
    assert info is not None
    assert info.python_version != ""
    assert info.os_name != ""


# ===== TestHealthCheck =====
def test_health():
    hc = HealthChecker(project_root=".")
    s = hc.get_summary()
    assert "overall" in s and "passed" in s


# ===== TestNodeManager =====
def test_node_manager():
    nm = NodeManager(project_root=str(Path(__file__).parent.parent))
    assert nm is not None


# ===== TestWorkflowManager =====
def test_workflow_manager():
    wm = WorkflowManager(workflows_dir=str(Path(__file__).parent.parent / "data" / "workflows"))
    assert wm is not None


# ===== Run all =====
all_tests = [
    ("ModelMetadata: serialization", test_meta_serialization),
    ("ModelMetadata: status enum", test_status_enum),
    ("ModelMetadata: display name", test_model_type_display),
    ("ModelMetadata: formats", test_model_type_formats),
    ("ModelIndex: add/get", test_index_add_get),
    ("ModelIndex: persistence", test_index_persistence),
    ("ModelIndex: get_by_type", test_index_get_by_type),
    ("ModelIndex: remove", test_index_remove),
    ("ModelIndex: count_by_type", test_index_count_by_type),
    ("ModelIndex: get_all", test_index_get_all),
    ("ModelManager: init", test_mm_init),
    ("ModelManager: register", test_mm_register),
    ("ModelManager: get", test_mm_get),
    ("ModelManager: by_type", test_mm_by_type),
    ("ModelManager: counts", test_mm_counts),
    ("ModelManager: remove", test_mm_remove),
    ("ModelManager: stats", test_mm_stats),
    ("ModelManager: persistence", test_mm_persistence),
    ("ModelManager: scan", test_mm_scan),
    ("ModelManager: verify", test_mm_verify),
    ("ModelManager: verify missing", test_mm_verify_missing),
    ("ModelScanner: empty", test_scan_empty),
    ("ModelScanner: with files", test_scan_with_files),
    ("ModelScanner: nonexistent", test_scan_nonexistent),
    ("ModelVerifier: sha256", test_sha256),
    ("ModelVerifier: match", test_verify_match),
    ("ModelVerifier: mismatch", test_verify_mismatch),
    ("ConfigManager: loads", test_config_loads),
    ("ConfigManager: nested", test_config_nested),
    ("ConfigManager: default", test_config_default),
    ("ConfigManager: gpu", test_config_gpu),
    ("Capability: registry singleton", test_registry_singleton),
    ("Capability: hub singleton", test_executor_singleton),
    ("Capability: output", test_output),
    ("Capability: param validate", test_param_validate),
    ("Capability: pipeline add", test_pipeline_add),
    ("Capability: pipeline validate", test_pipeline_validate_empty),
    ("Capability: pipeline remove", test_pipeline_remove),
    ("LauncherState: states exist", test_states_exist),
    ("LauncherState: values", test_state_values),
    ("LauncherState: property", test_state_property),
    ("LauncherState: transitions", test_state_transitions),
    ("ParamInfo: optional", test_paraminfo_optional),
    ("ParamInfo: default", test_paraminfo_default),
    ("Signatures: load", test_signatures_load),
    ("Signatures: all defined", test_all_defined),
    ("Logger: singleton", test_logger_singleton),
    ("Logger: DEBUG level", test_logger_level_debug),
    ("Logger: WARNING level", test_logger_level_warning),
    ("Logger: name", test_logger_name),
    ("StartupConfig: creation", test_startup_config),
    ("ConsoleWidget: escape", test_console_escape),
    ("StylesQSS: exists", test_styles),
    ("PortraitAPI: methods", test_portrait_methods),
    ("WorkflowParser: parse", test_workflow_parse),
    ("WorkflowParser: to_json", test_workflow_to_json),
    ("WorkflowParser: connection", test_connection_rt),
    ("BindingEngine: serialization", test_binding_rt),
    ("BindingEngine: basic", test_binding_engine),
    ("NodeSignature: create", test_sig_create),
    ("NodeSignature: roundtrip", test_sig_roundtrip),
    ("NodeRegistry: register", test_registry),
    ("EventBus: publish", test_event_publish),
    ("EventBus: once", test_event_once),
    ("I18n: load", test_i18n_load),
    ("I18n: fallback", test_i18n_fallback),
    ("ProjectStructure: root files", test_root_files),
    ("ProjectStructure: config files", test_config_files),
    ("ProjectStructure: src modules", test_src_modules),
    ("GPUDetector: detect", test_gpu_detect),
    ("GPUDetector: no crash nvidia", test_gpu_no_crash_nvidia),
    ("GPUDetector: system info", test_gpu_system_info),
    ("HealthCheck: summary", test_health),
    ("NodeManager: init", test_node_manager),
    ("WorkflowManager: init", test_workflow_manager),
]

print(f"Running {len(all_tests)} tests...\n")
for name, func in all_tests:
    run(name, func)

print(f"\n{'='*50}")
print(f"Results: {results['passed']} passed, {results['failed']} failed, {results['errors']} errors")
if failures:
    print("\nFailures:")
    for n, e in failures:
        print(f"  FAIL: {n}: {e}")
if errors:
    print("\nErrors:")
    for n, e in errors:
        print(f"  ERROR: {n}: {e}")
print("=" * 50)

if results["failed"] or results["errors"]:
    sys.exit(1)
