import argparse
import os
from packaging.version import Version
from typing import List

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import ensure, extract_system_components, fix_limits_h, overlayfs_ro, touch
from module.util import cflags_A, cflags_C, configure, make_custom, make_default, make_destdir_install

def _binutils(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.binutils / f'build-MMG-{arch}'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_MMC.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--target={arch}-linux-gnu',
      f'--build={config.build}',
      # prefer static
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-gprofng',
      '--disable-install-libbfd',
      '--disable-multilib',
      '--disable-nls',
      '--disable-werror',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MMG.binutils)

def _linux_headers(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  KARCH_MAP = {
    'aarch64': 'arm64',
    'x86_64': 'x86',
  }

  layer_MMG = paths.layer_MMG(arch)
  prefix = layer_MMG.linux / f'usr/local/{arch}-linux-gnu'

  make_custom(paths.src_dir.linux, [
    'headers_install',
    f'ARCH={KARCH_MAP[arch]}',
    f'INSTALL_HDR_PATH={prefix}',
  ], config.jobs)

  # remove hidden files `.install` and `..install.cmd`
  for file in prefix.glob('**/.install'):
    file.unlink()
  for file in prefix.glob('**/..install.cmd'):
    file.unlink()

def _gcc_1(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  layer_MMG = paths.layer_MMG(arch)
  libexec_target = layer_MMG.gcc / f'usr/local/lib/gcc/{arch}-linux-gnu'

  build_dir = paths.src_dir.gcc / f'build-MMG-{arch}'
  ensure(build_dir)

  config_flags: List[str] = []

  if v.major >= 13:
    config_flags.append('--with-gcc-major-version-only')
    limits_h = libexec_target / f'{v.major}/include/limits.h'
  elif v.major >= 7:
    config_flags.append('--with-gcc-major-version-only')
    limits_h = libexec_target / f'{v.major}/include-fixed/limits.h'
  else:
    limits_h = libexec_target / f'{ver.gcc}/include-fixed/limits.h'

  if v.major >= 6:
    config_flags += [
      '--enable-default-pie',
      '--enable-host-pie',
    ]

  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.gmp / 'usr/local',
    paths.layer_MMM.mpc / 'usr/local',
    paths.layer_MMM.mpfr / 'usr/local',
    paths.layer_MMC.zlib / 'usr/local',

    layer_MMG.binutils / 'usr/local',
    layer_MMG.linux / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local',
      '--libexecdir=/usr/local/lib',
      f'--target={arch}-linux-gnu',
      f'--build={config.build}',
      # prefer static
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-bootstrap',
      '--enable-checking=release',
      '--enable-languages=c,c++',
      '--disable-libatomic',
      '--disable-libgomp',
      '--disable-libmpx',
      '--disable-libsanitizer',
      '--disable-multilib',
      '--disable-nls',
      # packages
      f'--with-glibc-version={ver.glibc}',
      '--without-libcc1',
      '--with-system-zlib',
      *config_flags,
      *cflags_A(),
      *cflags_C('_FOR_TARGET'),
    ])

    make_custom(build_dir, ['all-gcc'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={layer_MMG.gcc}',
      'install-gcc',
    ], jobs = 1)

  fix_limits_h(limits_h, paths.src_dir.gcc)

def _gcc_2(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.gcc / f'build-MMG-{arch}'

  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.gmp / 'usr/local',
    paths.layer_MMM.mpc / 'usr/local',
    paths.layer_MMM.mpfr / 'usr/local',

    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.glibc / 'usr/local',
    layer_MMG.linux / 'usr/local',
  ]):
    make_custom(build_dir, ['all-target-libgcc'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={layer_MMG.gcc}',
      'install-target-libgcc',
    ], jobs = 1)

def _gcc_3(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.gcc / f'build-MMG-{arch}'

  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.gmp / 'usr/local',
    paths.layer_MMM.mpc / 'usr/local',
    paths.layer_MMM.mpfr / 'usr/local',

    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.glibc / 'usr/local',
    layer_MMG.linux / 'usr/local',
  ]):
    make_custom(build_dir, ['all-target'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={layer_MMG.gcc}',
      'install-target',
    ], jobs = 1)

def _glibc_1(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.glibc)
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.glibc / f'build-MMG-{arch}'
  ensure(build_dir)

  dest_prefix = layer_MMG.glibc / f'usr/local/{arch}-linux-gnu'

  config_flags: List[str] = []

  # workaround libunwind detection
  # not sure fixed in 2.25 or 2.26
  if v < Version('2.26'):
    config_flags.append('libc_cv_forced_unwind=yes')

  with overlayfs_ro('/usr/local', [
    # glibc prior to 2.31 can not be built with make 4.4 (infinite recursion)
    # upstream accidentally fixed it, cherry-pick seems very hard
    # the workaround is to build with make at that time
    # ref. https://github.com/crosstool-ng/crosstool-ng/issues/1932#issuecomment-1528139734
    paths.layer_MMM.make / 'usr/local',

    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.linux / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{arch}-linux-gnu',
      f'--host={arch}-linux-gnu',
      f'--build={config.build}',
      # static-only is not supported
      # here we build with dynamic library enabled ...
      '--enable-shared',
      '--enable-static',
      '--enable-static-nss',
      # features
      '--disable-build-nscd',
      '--disable-fortify-source',
      f'--enable-kernel={ver.enable_kernel(arch)}',
      '--disable-multi-arch',
      '--disable-nscd',
      '--disable-timezone-tools',
      '--disable-werror',
      *config_flags,
      *cflags_C(),
      # disable C++ to avoid -lgcc_s in test links-dso-program
      # which is not supported by static compiler
      'CXX=false',
    ])

    make_custom(build_dir, [
      f'DESTDIR={layer_MMG.glibc}',
      'install-headers',
    ], jobs = 1)

  touch(dest_prefix / 'include/gnu/stubs.h')

def _glibc_2(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.glibc)
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.glibc / f'build-MMG-{arch}'

  dest_prefix = layer_MMG.glibc / f'usr/local/{arch}-linux-gnu'

  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.make / 'usr/local',

    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.glibc / 'usr/local',
    layer_MMG.linux / 'usr/local',
  ]):
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MMG.glibc)

  base_prefix = layer_MMG.glibc / f'usr/local/{arch}-linux-gnu'
  sys_prefix = layer_MMG.glibc_sys / f'usr/local/{arch}-linux-gnu'

  # ... and then extract the dynamic library (and other stuff)
  sys_dirs = ['bin', 'etc', 'lib/gconv', 'libexec', 'sbin', 'share', 'var']
  # not sure since 2.19 or 2.20
  if v >= Version('2.20'):
    sys_dirs.append('lib/audit')

  extract_system_components(
    base_prefix,
    sys_prefix,
    lib_patterns=['lib/*.so*'],
    include_dirs=sys_dirs,
  )

def build_MMG_compiler(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _binutils(arch, ver, paths, config)
  _linux_headers(arch, ver, paths, config)
  _gcc_1(arch, ver, paths, config)
  _glibc_1(arch, ver, paths, config)
  _gcc_2(arch, ver, paths, config)
  _glibc_2(arch, ver, paths, config)
  _gcc_3(arch, ver, paths, config)

def _gmp(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gmp)
  v_gcc = Version(ver.gcc)
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.gmp / f'build-MMG-{arch}'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('6.4.0'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.glibc / 'usr/local',
    layer_MMG.linux / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{arch}-linux-gnu',
      f'--host={arch}-linux-gnu',
      f'--build={config.build}',
      '--disable-assembly',
      '--enable-static',
      '--disable-shared',
      *cflags_C(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MMG.gmp)

def _mpfr(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.mpfr / f'build-MMG-{arch}'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.glibc / 'usr/local',
    layer_MMG.linux / 'usr/local',

    layer_MMG.gmp / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{arch}-linux-gnu',
      f'--host={arch}-linux-gnu',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_C(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MMG.mpfr)

def _mpc(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  layer_MMG = paths.layer_MMG(arch)
  build_dir = paths.src_dir.mpc / f'build-MMG-{arch}'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.glibc / 'usr/local',
    layer_MMG.linux / 'usr/local',

    layer_MMG.gmp / 'usr/local',
    layer_MMG.mpfr / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{arch}-linux-gnu',
      f'--host={arch}-linux-gnu',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_C(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MMG.mpc)

def build_MMG_library(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmp(arch, ver, paths, config)

  _mpfr(arch, ver, paths, config)

  _mpc(arch, ver, paths, config)
