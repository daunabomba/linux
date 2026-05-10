import subprocess
import os
import multiprocessing
import shutil
from pathlib import Path
from mods.filelist import generate_list
import sys
from mods.utils import get_kernel_arch
from mods.build import get_build_env

def get_ktarget(arch):
    if arch in ["x32", "x86_64"]:
        return "bzImage"
    return "Image.gz"

def target_configure(staging_dir: Path, image_dir: Path, arch="x32", kconfig: Path = None):
    karch = get_kernel_arch(arch)
    print(f"Kernel ({arch}/{karch}): target_configure")
    repo_root = Path(__file__).parent.parent
    config_dst = repo_root / ".config"

    if not config_dst.exists():
        if kconfig and kconfig.exists():
            print(f"Kernel: Copying config from {kconfig}")
            shutil.copy(kconfig, config_dst)
        else:
            print(f"Error: Required kernel config missing or not found: {kconfig}")
            sys.exit(1)
    else:
        print(f"Kernel: Using existing .config")
    
    # Standard kernel build environment
    env = get_build_env()

    # Pre-configure steps
    (repo_root / ".scmversion").write_text("")
    (repo_root / "initfilelist").write_text("")
    (repo_root / ".version").unlink(missing_ok=True)

    cmd = [
        "make",
        "V=1",
        "LLVM=1",
        "HOSTCC=clang",
        "CC=clang",
        f"ARCH={karch}",
        "oldconfig"
    ]
    subprocess.run(cmd, cwd=repo_root, env=env, check=True)

def target_build(staging_dir: Path, image_dir: Path, arch="x32", kconfig: Path = None):
    karch = get_kernel_arch(arch)
    print(f"Kernel ({arch}/{karch}): target_build (vmlinux modules)")
    repo_root = Path(__file__).parent.parent
    make_jobs = multiprocessing.cpu_count()

    cmd = [
        "make",
        f"-j{make_jobs}",
        "V=1",
        "LLVM=1",
        f"ARCH={karch}",
        "vmlinux",
        "modules"
    ]
    subprocess.run(cmd, cwd=repo_root, env=get_build_env(), check=True)

def target_install(staging_dir: Path, image_dir: Path, arch="x32", kconfig: Path = None):
    karch = get_kernel_arch(arch)
    ktarget = get_ktarget(arch)
    print(f"Kernel ({arch}/{karch}): target_install (modules_install, generate_list, {ktarget})")
    repo_root = Path(__file__).parent.parent
    env = get_build_env()
    make_jobs = multiprocessing.cpu_count()

    # 1. Modules install
    cmd_mod = [
        "make",
        "V=1",
        "LLVM=1",
        f"ARCH={karch}",
        "HOSTCC=clang",
        "CC=clang",
        f"INSTALL_MOD_PATH={image_dir}",
        "modules_install"
    ]
    subprocess.run(cmd_mod, cwd=repo_root, env=env, check=True)

    # ... rest ...
    # 2. Cleanup before image build
    usr_path = repo_root / "usr"
    if usr_path.exists():
        subprocess.run("rm -f usr/.gen* usr/.bu* usr/*.a usr/*.cpio usr/*.o usr/.initramfs_*",
                       shell=True, cwd=repo_root, check=False)

    # 3. Generate file list for initramfs
    init_list_path = repo_root / "initfilelist"
    print(f"Kernel: Generating initramfs list to {init_list_path} from {image_dir}")
    
    ignore_patterns = [
        r'\.gitkeep$', 
        r'^linuxrc$', 
        r'^usr/man($|/)', 
        r'^usr/share/libc\+\+($|/)', 
        r'^usr/share/man($|/)'
    ]

    config_path = repo_root / ".config"
    if config_path.exists():
        if "CONFIG_MODULES=y" not in config_path.read_text():
            print("Kernel: CONFIG_MODULES=y not found in .config, excluding /usr/lib/modules")
            ignore_patterns.append(r'^usr/lib/modules($|/)')

    generate_list(str(image_dir), output_file=str(init_list_path), ignore_patterns=ignore_patterns)

    # 4. Final kernel image (bzImage/Image.gz) with initramfs
    cmd_img = [
        "make",
        f"-j{make_jobs}",
        "LLVM=1",
        f"ARCH={karch}",
        "HOSTCC=clang",
        "CC=clang",
        f"{ktarget}"
    ]
    subprocess.run(cmd_img, cwd=repo_root, env=env, check=True)
