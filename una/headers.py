#!/usr/bin/python3
import shutil
import subprocess
import os
from pathlib import Path
from mods.utils import get_kernel_arch

"""Linux kernel headers install (usr/include/linux → staging)"""

def get_env():
    env = os.environ.copy()
    # Path to our tools-built LLVM tools
    tools_bin = Path(__file__).parent.parent.parent.parent / "bld" / "tools" / "bin"
    env["PATH"] = f"{tools_bin}:{env.get('PATH', '')}"
    return env


def target_configure(staging_dir, target_dir, arch, kconfig):
    """Prepare kernel .config"""
    repo_root = Path(__file__).parent.parent
    # Use provided config
    config_path = Path(kconfig)
    config_dst = repo_root / ".config"
    shutil.copy(config_path, config_dst)

    karch = get_kernel_arch(arch)
    env = get_env()

    cmd_img = [
        "make",
        "LLVM=1",
        f"ARCH={karch}",
        "HOSTCC=clang",
        "CC=clang",
        "olddefconfig"
    ]
    subprocess.run(cmd_img, cwd=repo_root, env=env, check=True)

def target_headers_install(staging_dir, target_dir, arch, kconfig):
    """Install public headers to staging/usr/include"""
    repo_root = Path(__file__).parent.parent
    
    karch = get_kernel_arch(arch)
    env = get_env()

    cmd_img = [
        "make",
        "LLVM=1",
        f"ARCH={karch}",
        "HOSTCC=clang",
        "CC=clang",
        "headers_install",
        f"INSTALL_HDR_PATH={staging_dir}/usr",
    ]
    subprocess.run(cmd_img, cwd=repo_root, env=env, check=True)

    # Cleanup internal headers (Kbuild filters most)
    internal = ["generated"]
    for hdr_dir in internal:
        hdr_path = staging_dir / "usr/include" / hdr_dir 
        if hdr_path.exists(): shutil.rmtree(hdr_path)
    
    print(f"Kernel headers installed for {arch}")
