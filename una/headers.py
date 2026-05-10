#!/usr/bin/python3
import shutil
import subprocess
import os
from pathlib import Path
from mods.utils import get_kernel_arch
from mods.build import get_build_env, SubprocessRunner

"""Linux kernel headers install (usr/include/linux → staging)"""

# Module-level runner, initialized when needed
_runner = None

def _get_runner(trace_file=None):
    """Get or create the subprocess runner."""
    global _runner
    if _runner is None:
        _runner = SubprocessRunner(trace_file)
    return _runner

def set_trace_file(trace_file):
    """Set the trace file for subprocess logging."""
    global _runner
    _runner = SubprocessRunner(trace_file)


def target_configure(staging_dir, target_dir, arch, kconfig):
    """Prepare kernel .config"""
    repo_root = Path(__file__).parent.parent
    # Use provided config
    config_path = Path(kconfig)
    config_dst = repo_root / ".config"
    shutil.copy(config_path, config_dst)

    karch = get_kernel_arch(arch)
    env = get_build_env()

    cmd_img = [
        "make",
        "V=1",
        "LLVM=1",
        f"ARCH={karch}",
        "HOSTCC=clang",
        "CC=clang",
        "olddefconfig"
    ]
    _get_runner().run(cmd_img, cwd=repo_root, env=env, check=True)

def target_headers_install(staging_dir, target_dir, arch, kconfig):
    """Install public headers to staging/usr/include"""
    repo_root = Path(__file__).parent.parent
    
    karch = get_kernel_arch(arch)
    env = get_build_env()

    cmd_img = [
        "make",
        "V=1",
        "LLVM=1",
        f"ARCH={karch}",
        "HOSTCC=clang",
        "CC=clang",
        "headers_install",
        f"INSTALL_HDR_PATH={staging_dir}/usr",
    ]
    _get_runner().run(cmd_img, cwd=repo_root, env=env, check=True)

    # Cleanup internal headers (Kbuild filters most)
    internal = ["generated"]
    for hdr_dir in internal:
        hdr_path = staging_dir / "usr/include" / hdr_dir 
        if hdr_path.exists(): shutil.rmtree(hdr_path)
    
    print(f"Kernel headers installed for {arch}")
