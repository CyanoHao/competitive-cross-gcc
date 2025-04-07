import argparse
import os
import shutil
from packaging.version import Version
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import overlayfs_ro
from module.util import cflags_A, configure, ensure, make_default, make_destdir_install

def _gmp(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gmp / 'build-MMM'
  ensure(build_dir)
  configure(build_dir, [
    '--prefix=/usr/local',
    f'--host={config.build}',
    f'--build={config.build}',
    '--disable-assembly',
    '--enable-static',
    '--disable-shared',
    *cflags_A(),
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_MMM.gmp)

def _mpfr(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.gmp / 'usr/local',
  ]):
    build_dir = paths.src_dir.mpfr / 'build-MMM'
    ensure(build_dir)
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--host={config.build}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMM.mpfr)

def _mpc(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.gmp / 'usr/local',
    paths.layer_MMM.mpfr / 'usr/local',
  ]):
    build_dir = paths.src_dir.mpc / 'build-MMM'
    ensure(build_dir)
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--host={config.build}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMM.mpc)

def _zlib_net(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.zlib_net / 'build-MMM'
  ensure(build_dir)
  configure(build_dir, [
    '--prefix=/usr/local',
    '--static',
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_MMM.zlib)

def build_MMM_library(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmp(ver, paths, config)
  _mpfr(ver, paths, config)
  _mpc(ver, paths, config)
  _zlib_net(ver, paths, config)

def _gmake(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.make)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.make / 'build-MMM'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('4.5'):
    c_extra.append('-std=gnu11')

  configure(build_dir, [
    '--prefix=/usr/local',
    f'--build={config.build}',
    '--disable-nls',
    *cflags_A(c_extra = c_extra),
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_MMM.make)

def _python(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.zlib / 'usr/local',
  ]):
    build_dir = paths.src_dir.python / 'build-MMM'
    ensure(build_dir)
    configure(build_dir, [
      f'--prefix=/usr/local',
      # static
      '--disable-shared',
      'MODULE_BUILDTYPE=static',
      # features
      '--disable-test-modules',
      # packages
      '--without-static-libpython',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMM.python)

def build_MMM_tool(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmake(ver, paths, config)
  _python(ver, paths, config)
