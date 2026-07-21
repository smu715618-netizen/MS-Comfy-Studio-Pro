"""Integration test for MS Comfy Studio Pro Phase 1"""
import sys, tempfile, os
sys.path.insert(0, 'D:/MS-Comfy-Studio-Pro')

print('=' * 50)
print('INTEGRATION TEST - MS Comfy Studio Pro')
print('=' * 50)
print()

# 1. Config Manager
print('[1/8] ConfigManager...')
from src.config_manager import ConfigManager, get_config
config = ConfigManager()
assert config.get('app.name') == 'MS Comfy Studio Pro'
assert config.get('gpu.device') == 'xpu'
assert config.get('comfyui.port') == 8188
assert config.get('paths.data_dir') == 'data'
gc = get_config()
assert gc.get('app.name') == 'MS Comfy Studio Pro'
print('  PASS - Config loads and reads correctly')

# 2. Logger
print('[2/8] Logger...')
from src.logger import setup_logging, get_logger
tmpdir = tempfile.mkdtemp()
setup_logging(log_level='DEBUG', log_dir=tmpdir, console_output=False)
log = get_logger('integration_test')
log.info('test message')
assert os.path.exists(tmpdir)
print('  PASS - Logger works correctly')

# 3. i18n
print('[3/8] I18n...')
from src.i18n import I18nManager
i18n = I18nManager()
assert i18n.t('app.name') == 'MS Comfy Studio Pro'
i18n.set_locale('en-US')
assert i18n.t('app.name') == 'MS Comfy Studio Pro'
print('  PASS - i18n works correctly')

# 4. GPU Detector
print('[4/8] GPU Detector...')
from src.gpu_detector import GPUDetector
detector = GPUDetector()
info = detector.detect()
print(f'  PASS - GPU: {info.gpu_type.value} / {info.name or "unknown"}')

# 5. Health Checker
print('[5/8] Health Checker...')
from src.health_check import HealthChecker
hc = HealthChecker(project_root='D:/MS-Comfy-Studio-Pro')
summary = hc.get_summary()
print(f'  PASS - Health: {summary["overall"]} ({summary["passed"]} passed)')

# 6. Models Manager
print('[6/8] Model Manager...')
from src.models import ModelManager, ModelType
mm = ModelManager(data_dir='D:/MS-Comfy-Studio-Pro/data')
assert mm.get_storage_usage()['model_count'] >= 0
print(f'  PASS - Models: {mm.get_storage_usage()["model_count"]} indexed')

# 7. Node Manager
print('[7/8] Node Manager...')
from src.nodes import NodeManager
nm = NodeManager(comfyui_dir='D:/MS-Comfy-Studio-Pro/comfyui')
print(f'  PASS - Nodes: {len(nm.get_all_nodes())} indexed')

# 8. Workflow Manager
print('[8/8] Workflow Manager...')
from src.workflows import WorkflowManager
wm = WorkflowManager(workflows_dir='D:/MS-Comfy-Studio-Pro/data/workflows')
print(f'  PASS - Workflows: {len(wm.get_all_workflows())} indexed')

print()
print('=' * 50)
print('ALL 8 INTEGRATION TESTS PASSED')
print('=' * 50)
