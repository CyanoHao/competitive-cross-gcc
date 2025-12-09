import argparse
import os
import shutil
from packaging.version import Version

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import ensure, overlayfs_ro
from module.util import cflags_C, configure, make_custom

def _gdbserver(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gdb)
  v_gcc = Version(ver.gcc)
  layer_AAC = paths.layer_AAC(arch)
  layer_ACC = paths.layer_ACC(arch)
  build_dir = paths.src_dir.gdb / f'build-ACC-{arch}'
  ensure(build_dir)

  destdir = layer_ACC.gdb / f'{arch}-linux-gnu'

  with overlayfs_ro('/usr/local', [
    layer_AAC.binutils / 'usr/local',
    layer_AAC.gcc / 'usr/local',
    layer_AAC.glibc / 'usr/local',
    layer_AAC.linux / 'usr/local',

    layer_AAC.gmp / 'usr/local',
    layer_AAC.mpc / 'usr/local',
    layer_AAC.mpfr / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--target={arch}-linux-gnu',
      f'--host={arch}-linux-gnu',
      f'--build={config.build}',
      # prefer static
      '--disable-inprocess-agent',
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-sim',
      '--disable-tui',
      # packages
      '--with-gdbserver',
      # libtool eats `-static`
      *cflags_C(ld_extra = ['--static']),
    ])

    if v.major >= 10:
      make_custom(build_dir, ['all-gdbserver'], config.jobs)
      make_custom(build_dir, [
        f'DESTDIR={destdir}',
        'install-gdbserver',
      ], jobs = 1)
    else:
      make_custom(build_dir, ['all-gdb'], config.jobs)
      make_custom(build_dir / 'gdb/gdbserver', [
        f'DESTDIR={destdir}',
        'install-only',
      ], jobs = 1)

def build_ACC_tool(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gdbserver(arch, ver, paths, config)
