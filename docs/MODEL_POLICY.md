# 模型管理策略 (Model Policy)

本文档记录 MS Comfy Studio Pro 的模型管理原则与策略。

---

## 核心原则

### 1. 程序与模型解耦

- 安装包不含任何模型文件
- 模型按需下载，不捆绑分发
- 安装包体积控制在合理范围内

### 2. 模型按需下载

- 用户首次使用时才下载所需模型
- 支持断点续传和多线程下载
- 下载进度可视化反馈

### 3. 插件按需安装

- 节点和插件独立于核心安装
- 用户可选择安装社区节点
- 插件版本与 ComfyUI 版本解耦

### 4. 工作流独立升级

- 工作流 JSON 文件可独立于程序升级
- 支持工作流模板市场
- 工作流版本管理

---

## 模型分类

| 类型 | 用途 | 典型大小 | 存储位置 |
|------|------|----------|----------|
| Checkpoint | 主生成模型 | 2-7 GB | data/models/checkpoints/ |
| VAE | 解码器 | 0.1-0.3 GB | data/models/vae/ |
| CLIP | 文本编码器 | 0.3-0.7 GB | data/models/clip/ |
| UNet | 扩散模型 | 2-7 GB | data/models/unet/ |
| LoRA | 微调模型 | 0.01-0.2 GB | data/models/lora/ |
| ControlNet | 控制模型 | 0.4-2 GB | data/models/controlnet/ |
| Upscale | 超分辨率 | 0.01-0.1 GB | data/models/upscale/ |
| Embedding | 文本嵌入 | 0.001-0.01 GB | data/models/embedding/ |

---

## 模型来源

### 优先来源

1. **Hugging Face** — 开源模型的主要分发渠道
2. **ComfyUI 官方节点** — 内置节点所需的模型

### 备选来源

3. **Civitai** — 社区模型分享平台
4. **本地文件** — 用户手动导入的模型

### 来源配置

```yaml
models:
  default_source: "huggingface"
  sources:
    huggingface:
      name: "Hugging Face"
      base_url: "https://huggingface.co"
    civitai:
      name: "Civitai"
      base_url: "https://civitai.com"
```

---

## 模型验证

### SHA256 校验

每个模型文件记录 SHA256 哈希值，下载完成后自动校验。

### 完整性检查

- 下载完成后自动验证文件完整性
- 损坏的模型会被标记并允许重新下载
- 健康检查模块会扫描所有模型的完整性

### 缓存策略

- 已验证的模型不会被重复下载
- 支持增量更新（仅下载差异部分）

---

## 未来方向

### 模型压缩与量化

- 探索 INT8 / FP8 量化降低显存占用
- 针对 8GB VRAM 的模型压缩方案
- 支持用户自定义量化级别

### 模型推荐

- 根据硬件配置推荐合适的模型
- 根据使用场景（证件照/修图/放大）推荐预置模型
- 模型大小与显存的自动匹配

### 模型共享

- 支持团队间模型共享
- 模型去重（同一模型只存储一份）
- 模型版本管理

---

## 注意事项

> 当前阶段模型管理仅为框架层面，实际的下载、验证、管理 UI 将在后续阶段实现。
