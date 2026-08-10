# 平台适配层

跨平台 GPU 后端管理模块。

按当前操作系统自动加载对应的 GPU 后端模块：
- Windows: Intel XPU / DirectML (NVIDIA CUDA 预留)
- macOS: Apple Metal (MPS)
- Linux: ROCm / CUDA / XPU

所有平台模块在启动时根据运行环境懒加载，
避免未使用的 GPU 后端占用内存空间。

## 目录结构

```
platform/
├── __init__.py          # 平台检测和路由
├── windows/
│   └── __init__.py      # Windows GPU 后端
├── macos/
│   └── __init__.py      # macOS GPU 后端 (预留)
└── linux/
    └── __init__.py      # Linux GPU 后端 (预留)
```

## 使用方式

```python
from platform import get_platform, Platform

platform = get_platform()
if platform == Platform.WINDOWS:
    from platform.windows import check_xpu_available
    # ...
```
