import argparse
from packaging.version import Version
import shutil
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import ensure, overlayfs_ro, remove_info_main_menu
from module.util import cflags_B, configure, make_default, make_destdir_install
from module.util import xmake_build, xmake_config, xmake_install

def _gmake(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.make)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.make / 'build-ABB'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('4.5'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      '--program-prefix=mingw32-',
      '--host=x86_64-w64-mingw32',
      f'--build={config.build}',
      *cflags_B(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_ABB.make)

  remove_info_main_menu(paths.layer_ABB.make)

  license_dir = paths.layer_ABB.make / 'share/licenses/make'
  ensure(license_dir)
  shutil.copy(paths.src_dir.make / 'COPYING', license_dir / 'COPYING')

def _xmake(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.xmake / 'usr/local',

    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
  ]):
    build_dir = paths.src_dir.xmake / 'core'
    xmake_config(build_dir, [
      '--plat=mingw',
      '--arch=x86_64',
    ])
    xmake_build(build_dir, config.jobs)
    xmake_install(build_dir, paths.layer_ABB.xmake, ['cli'])

  license_dir = paths.layer_ABB.xmake / 'share/licenses/xmake'
  ensure(license_dir)
  shutil.copy(paths.src_dir.xmake / 'LICENSE.md', license_dir / 'LICENSE.md')

def build_ABB_tool(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmake(ver, paths, config)
  _xmake(ver, paths, config)
