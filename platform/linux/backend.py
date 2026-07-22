# Linux GPU 后端模块 (预留)

'''Linux平台GPU管理 — 预留接口'''

import sys


def get_backend_type():
    return 'linux'


def check_cuda_available():
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def generate_launch_args(vram_mode='normal_vram'):
    args = []
    if vram_mode == 'low_vram':
        args.extend(['--low-vram'])
    elif vram_mode == 'high_vram':
        args.extend(['--high-vram'])
    return args


def get_compatible_backends():
    backends = []
    if check_cuda_available():
        backends.append('cuda')
    if not backends:
        backends.append('cpu')
    return backends


if __name__ == '__main__':
    print(f'Backend: {get_backend_type()}')
    print(f'CUDA: {check_cuda_available()}')
    print(f'Backends: {get_compatible_backends()}')
