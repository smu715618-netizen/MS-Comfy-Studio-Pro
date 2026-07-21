# 硬件配置档案 (Hardware Profile)

本文档记录 MS Comfy Studio Pro 的目标硬件配置及扩展策略。

---

## 当前目标平台

### Intel Arc A750 8GB

| 项目 | 规格 |
|------|------|
| GPU | Intel Arc A750 |
| 显存 | 8 GB GDDR6 |
| CPU | Intel Core i5-10400 或同级 |
| 内存 | 16 GB RAM |
| 系统 | Windows 11 (22H2+) |
| 存储 | 50 GB SSD（推荐） |

**设计目标：** 在此配置下目标优化运行效果，确保所有默认工作流可稳定运行。

**性能优先级：**
1. Intel XPU (PyTorch XPU 后端) — 主路线，性能最优
2. DirectML (Windows DirectX 12 抽象层) — 备用路线，兼容性好
3. CPU Only — 最后兜底方案

### 8GB VRAM 约束

以下配置针对 8GB 显存进行了调优：

```yaml
gpu:
  memory_optimization:
    max_batch_size: 1           # 单批次推理
    fp16_precision: true        # FP16 降低显存占用
    attention_slicing: true     # Attention 切片减少峰值
    vae_chunk_size: 4           # VAE 分块解码
```

参见 `configs/xpu.yaml` 和 `configs/default.yaml` 中的详细配置。

---

## 后续扩展策略

### NVIDIA CUDA（预留）

当未来支持 NVIDIA GPU 时：

- 检测顺序放在 Intel 之后（当前平台专注 Intel Arc）
- 使用 PyTorch CUDA 后端
- 利用 cuDNN / TensorRT 加速
- 显存管理策略类似，但可利用 tensor cores

**何时启用：** 用户明确要求 NVIDIA 支持时

### AMD ROCm（预留）

当未来支持 AMD GPU 时：

- 检测顺序放在 NVIDIA 之后
- 使用 PyTorch ROCm 后端
- 依赖 rocm-smi 工具链

**何时启用：** AMD RDNA3 + MI300 系列成熟后评估

### Apple Silicon / macOS（预留）

当未来支持 macOS 时：

- 使用 Metal Performance Shaders (MPS)
- PyTorch MPS 后端
- 统一内存架构简化显存管理
- 独立构建流程（不同依赖树）

**何时启用：** 收到明确 macOS 用户需求时

---

## 跨平台加载策略

为确保启动时无需同时加载所有 GPU 后端：

1. 运行时自动检测当前平台和设备
2. 仅加载对应的 GPU 后端模块
3. 未使用的后端代码不进入内存空间
4. 通过配置文件 `preferred_type` 控制优先选项

```python
# 伪代码示例
if system == "windows" and gpu == "intel":
    import torch.xpu  # 仅加载 XPU
elif system == "windows" and gpu == "nvidia":
    import torch.cuda  # 仅加载 CUDA
elif system == "macos":
    import torch.mps   # 仅加载 MPS
```

---

## 最低配置验证

安装时自动检查：

```bash
mcsp health
```

输出示例：

```
[health] overall: healthy, passed: 7/7
  [pass] gpu: GPU: Intel Arc A750 (intel_xpu)
  [pass] python: Python 3.11.9
  [pass] disk_space: 磁盘空间充足: 剩余 120.5GB / 512.0GB
  [warn] network: HuggingFace 不可达
  [pass] dependencies: 所有核心依赖已安装
  [warn] comfyui: ComfyUI 尚未安装，请运行 'mcsp setup'
  [pass] data_dirs: 数据目录结构完整
```
