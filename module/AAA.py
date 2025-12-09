import argparse
import os
import shutil
from packaging.version import Version
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import overlayfs_ro
from module.util import cflags_L, configure, ensure, make_default, make_destdir_install

def _gmp(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gmp / 'build-AAA'
  ensure(build_dir)
  configure(build_dir, [
    '--prefix=/usr/local',
    f'--host={config.build}',
    f'--build={config.build}',
    '--disable-assembly',
    '--enable-static',
    '--disable-shared',
    *cflags_L(),
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_AAA.gmp)

def _mpfr(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
  ]):
    build_dir = paths.src_dir.mpfr / 'build-AAA'
    ensure(build_dir)
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--host={config.build}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_L(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAA.mpfr)

def _mpc(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
    paths.layer_AAA.mpfr / 'usr/local',
  ]):
    build_dir = paths.src_dir.mpc / 'build-AAA'
    ensure(build_dir)
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--host={config.build}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_L(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAA.mpc)

def _z(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.z / 'build-AAA'
  ensure(build_dir)
  configure(build_dir, [
    '--prefix=/usr/local',
    '--static',
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_AAA.z)

def build_AAA_library(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmp(ver.gmp, paths, config)

  _mpfr(ver.mpfr, paths, config)

  _mpc(ver.mpc, paths, config)

  _z(ver, paths, config)

def _gmake(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.make)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.make / 'build-AAA'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('4.5'):
    c_extra.append('-std=gnu11')

  configure(build_dir, [
    '--prefix=/usr/local',
    f'--build={config.build}',
    '--disable-nls',
    *cflags_L(c_extra = c_extra),
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_AAA.make)

def _python(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.z / 'usr/local',
  ]):
    build_dir = paths.src_dir.python / 'build-AAA'
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
      *cflags_L(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAA.python)

def _xmake(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  subprocess.run([
    './configure',
    '--prefix=/usr/local',
  ], cwd = paths.src_dir.xmake, check = True)
  make_default(paths.src_dir.xmake, config.jobs)
  make_destdir_install(paths.src_dir.xmake, paths.layer_AAA.xmake)

def build_AAA_tool(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmake(ver, paths, config)

  if ver.python:
    _python(ver, paths, config)

  _xmake(ver, paths, config)
