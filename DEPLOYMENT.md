# 部署说明

## 生产环境部署

### 1. 服务器部署

```bash
# 克隆项目
git clone <repository-url> MS-Comfy-Studio-Pro
cd MS-Comfy-Studio-Pro

# 安装依赖
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-xpu.txt

# 克隆 ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git

# 创建 systemd 服务 (Linux) 或 Windows Service
```

### 2. 后台服务模式

创建 Windows 服务（使用 nssm）：

```bash
# 安装 NSSM
choco install nssm

# 创建服务
nssm install MSComfyStudioPro "C:\Python311\python.exe" "-m src.cli start --port 8188"
nssm start MSComfyStudioPro
```

### 3. Docker 部署（未来计划）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "src.cli", "start"]
```

## 配置优化

### Intel Arc A750 性能优化

在 `configs/local.yaml` 中调整：

```yaml
gpu:
  memory_optimization:
    max_batch_size: 1        # 8GB VRAM 限制
    fp16_precision: true     # 启用 FP16
    attention_slicing: true  # 启用注意力切片
    vae_chunk_size: 4        # VAE 分块大小
```

### 显存预留

```yaml
xpu:
  shared_memory_limit_mb: 4096    # 共享内存上限
  performance_mode: "balanced"    # 平衡模式
```

## 安全注意事项

1. **不要暴露 ComfyUI 端口到公网**
2. **定期更新依赖和安全补丁**
3. **模型文件存储在安全位置**
4. **使用防火墙限制本地访问**

## 备份策略

### 需要备份的内容

- `configs/local.yaml` - 自定义配置
- `data/workflows/user/` - 用户工作流
- `data/models/` - 下载的模型（较大，可考虑云存储）

### 备份命令

```bash
# 备份配置和工作流
tar -czf mcsp-backup-$(date +%Y%m%d).tar.gz \
    configs/local.yaml \
    data/workflows/user/

# 恢复
tar -xzf mcsp-backup-YYYYMMDD.tar.gz
```

## 故障排除

### ComfyUI 启动失败

1. 检查虚拟环境是否正确激活
2. 确认 GPU 驱动已正确安装
3. 查看日志文件：`data/logs/mcsp_*.log`
4. 运行健康检查：`python -m src.cli health`

### 显存不足

1. 降低 `max_batch_size` 到 1
2. 启用 `attention_slicing`
3. 减少同时运行的工作流数量
4. 关闭其他占用 GPU 的应用程序

### 网络问题

1. 检查代理设置
2. 使用国内镜像源
3. 手动下载模型文件
