# 安装指南

## 系统要求

- **操作系统**: Windows 11 (22H2+)
- **Python**: 3.11.x（必须）
- **GPU**: Intel Arc A750 或更高
- **内存**: 16 GB RAM
- **磁盘**: 50 GB 可用空间

## 快速安装

### 方法一：一键安装（推荐）

1. 确保已安装 Python 3.11+
2. 双击运行 `setup.bat` 或在终端中运行：

```bash
.\setup.bat
```

3. 安装完成后，双击 `run_launcher.bat` 启动管理面板

### 方法二：PowerShell 安装

```powershell
.\setup.ps1
```

### 方法三：手动安装

```bash
# 1. 克隆项目
git clone <repository-url>
cd MS-Comfy-Studio-Pro

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 3. 安装核心依赖
pip install -r requirements.txt

# 4. 克隆 ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git

# 5. 安装 XPU 依赖
pip install -r requirements-xpu.txt
```

## 首次配置

### 1. 创建本地配置

首次安装后，可以创建本地配置文件来覆盖默认设置：

```bash
cp configs/default.yaml configs/local.yaml
```

然后编辑 `configs/local.yaml` 中的个性化设置。

### 2. 配置 Intel Arc 驱动

确保已安装最新的 Intel Arc 显卡驱动：

1. 前往 [Intel 驱动下载中心](https://www.intel.cn/content/www/cn/zh/download-center/home.html)
2. 下载并安装最新的 Arc 显卡驱动
3. 重启计算机

### 3. 验证安装

运行健康检查：

```bash
python -m src.cli health
```

## 启动

### 启动管理面板

```bash
run_launcher.bat
```

### 启动 ComfyUI

```bash
run_comfy.bat
```

### 使用 CLI 启动

```bash
# 启动 ComfyUI（默认端口 8188）
python -m src.cli start

# 指定端口
python -m src.cli start --port 8189

# 自动打开浏览器
python -m src.cli start --browser
```

## 常见问题

### Q: Python 版本不兼容

**A**: 请确保安装的是 Python 3.11.x。不支持 3.12+。

### Q: 虚拟环境创建失败

**A**: 确保 Python 已添加到系统 PATH，或者使用完整路径：

```bash
C:\Python311\python.exe -m venv venv
```

### Q: ComfyUI 克隆失败

**A**: 检查网络连接，或手动克隆：

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
```

### Q: Intel XPU 依赖安装失败

**A**: 尝试使用国内镜像源：

```bash
pip install -r requirements-xpu.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 卸载

运行 `uninstall.bat` 即可卸载。
