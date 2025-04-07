import argparse
import os
from packaging.version import Version
import shutil
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import common_MMC_layers, ensure, overlayfs_ro, remove_info_main_menu
from module.util import cflags_B, configure, make_default, make_destdir_install
from module.util import xmake_build, xmake_config, xmake_install

def _gmake(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.make)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.make / 'build-MCC'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('4.5'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    *common_MMC_layers(paths),

    paths.layer_MMC.intl / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      '--enable-nls',
      *cflags_B(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MCC.make)

  remove_info_main_menu(paths.layer_MCC.make)

  license_dir = paths.layer_MCC.make / 'share/licenses/make'
  ensure(license_dir)
  shutil.copy(paths.src_dir.make / 'COPYING', license_dir / 'COPYING')

def build_MCC_tool(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmake(ver, paths, config)
