import argparse
import glob
import os
from packaging.version import Version
import shutil
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import create_unprefixed_alias, ensure, fix_limits_h, overlayfs_ro, remove_info_main_menu
from module.util import cflags_M, cflags_G, configure, make_custom, make_default, make_destdir_install

def _binutils(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  layer_ABC = paths.layer_ABC(arch)
  build_dir = paths.src_dir.binutils / f'build-ABC-{arch}'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      '--host=x86_64-w64-mingw32',
      f'--target={arch}-linux-gnu',
      f'--build={config.build}',
      # workaround: bfd plugin 'dep' should be built as shared object
      '--enable-shared',
      '--enable-static',
      # features
      '--disable-install-libbfd',
      '--disable-multilib',
      '--disable-nls',
      *cflags_M(lto = True),
      'AR=x86_64-w64-mingw32-gcc-ar',
      'RANLIB=x86_64-w64-mingw32-gcc-ranlib',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_ABC.binutils)

  create_unprefixed_alias(layer_ABC.binutils, f'{arch}-linux-gnu')

  remove_info_main_menu(layer_ABC.binutils)

  license_dir = layer_ABC.binutils / 'share/licenses/binutils'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.binutils / file, license_dir / file)

def _linux_headers(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.linux)

  KARCH_MAP = {
    'aarch64': 'arm64',
    'x86_64': 'x86',
  }

  layer_ABC = paths.layer_ABC(arch)
  prefix = layer_ABC.linux / f'{arch}-linux-gnu'

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

  # netfilter has pairs of files that only differ in case
  # here we simply remove related headers
  for file in prefix.glob('include/linux/netfilter*'):
    if file.is_dir():
      shutil.rmtree(file)
    else:
      file.unlink()

  license_dir = layer_ABC.linux / 'share/licenses/linux'
  ensure(license_dir)
  shutil.copy(paths.src_dir.linux / 'COPYING', license_dir / 'COPYING')
  if v >= Version('4.19'):
    shutil.copy(paths.src_dir.linux / 'LICENSES/preferred/GPL-2.0', license_dir / 'GPL-2.0')
    shutil.copy(paths.src_dir.linux / 'LICENSES/exceptions/Linux-syscall-note', license_dir / 'Linux-syscall-note')

def _glibc(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.glibc)
  layer_AAC = paths.layer_AAC(arch)
  layer_ABC = paths.layer_ABC(arch)
  build_dir = paths.src_dir.glibc / f'build-ABC-{arch}'
  ensure(build_dir)

  destdir = layer_ABC.glibc / f'{arch}-linux-gnu'

  with overlayfs_ro('/usr/local', [
    # glibc prior to 2.31 can not be built with make 4.4 (infinite recursion)
    # upstream accidentally fixed it, cherry-pick seems very hard
    # the workaround is to build with make at that time
    # ref. https://github.com/crosstool-ng/crosstool-ng/issues/1932#issuecomment-1528139734
    paths.layer_AAA.make / 'usr/local',

    layer_AAC.binutils / 'usr/local',
    layer_AAC.gcc / 'usr/local',
    layer_AAC.glibc / 'usr/local',
    layer_AAC.linux / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--host={arch}-linux-gnu',
      f'--build={config.build}',
      # static-only is not supported
      # here we build with dynamic library enabled ...
      '--enable-share',
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
      *cflags_G(),
      # disable C++ to avoid -lgcc_s in test links-dso-program
      # which is not supported by static compiler
      'CXX=false',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, destdir)

  # ... and then remove the dynamic library (and other stuff)
  for file in destdir.glob('lib/*.so*'):
    file.unlink()
  remove_dirs = ['bin', 'etc', 'lib/gconv', 'libexec', 'sbin', 'share', 'var']
  # not sure since 2.19 or 2.20
  if v >= Version('2.20'):
    remove_dirs.append('lib/audit')
  for dir in remove_dirs:
    shutil.rmtree(f'{destdir}/{dir}')

  # fix libm.a reference path
  if (arch == 'x86_64' and v >= Version('2.25')) or (arch == 'aarch64' and v >= Version('2.38')):
    libm_content = open(f'{destdir}/lib/libm.a', 'r').read()
    with open(f'{destdir}/lib/libm.a', 'w') as f:
      f.write(libm_content.replace('/lib/', './'))

  license_dir = layer_ABC.glibc / 'share/licenses/glibc'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING.LIB', 'LICENSES']:
    shutil.copy(paths.src_dir.glibc / file, license_dir / file)

def _gcc(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  layer_AAC = paths.layer_AAC(arch)
  layer_ABC = paths.layer_ABC(arch)
  build_dir = paths.src_dir.gcc / f'build-ABC-{arch}'
  ensure(build_dir)

  libexec_target = layer_ABC.gcc / f'lib/gcc/{arch}-linux-gnu'

  config_flags = []

  if v.major >= 13:
    config_flags.append('--with-gcc-major-version-only')
    limits_h = libexec_target / f'{v.major}/include/limits.h'
  elif v.major >= 7:
    config_flags.append('--with-gcc-major-version-only')
    limits_h = libexec_target / f'{v.major}/include-fixed/limits.h'
  else:
    limits_h = libexec_target / f'{ver.gcc}/include-fixed/limits.h'

  if v.major >= 6:
    config_flags.append('--enable-default-pie')

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',

    paths.layer_AAB.gmp / 'usr/local',
    paths.layer_AAB.mpc / 'usr/local',
    paths.layer_AAB.mpfr / 'usr/local',

    layer_AAC.binutils / 'usr/local',
    layer_AAC.gcc / 'usr/local',
    layer_AAC.glibc / 'usr/local',
    layer_AAC.linux / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--libexecdir=/lib',
      '--host=x86_64-w64-mingw32',
      f'--target={arch}-linux-gnu',
      f'--build={config.build}',
      # static build
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-bootstrap',
      '--enable-checking=release',
      '--enable-languages=c,c++',
      '--disable-libmpx',
      '--disable-multilib',
      '--enable-nls',
      # packages
      '--without-libcc1',
      *config_flags,
      *cflags_M(lto = True),
      *cflags_G('_FOR_TARGET'),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_ABC.gcc)
    fix_limits_h(limits_h, paths.src_dir.gcc)

  create_unprefixed_alias(layer_ABC.gcc, f'{arch}-linux-gnu')

  remove_info_main_menu(layer_ABC.gcc)

  license_dir = layer_ABC.gcc / 'share/licenses/gcc'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.RUNTIME', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.gcc / file, license_dir / file)

def _gdb(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gdb)
  v_gcc = Version(ver.gcc)
  layer_AAC = paths.layer_AAC(arch)
  layer_ABC = paths.layer_ABC(arch)
  build_dir = paths.src_dir.gdb / f'build-ABC-{arch}'
  ensure(build_dir)

  python_flags = []
  c_extra = []

  if ver.python:
    python_flags.append(f'--with-python=/usr/local/x86_64-w64-mingw32/python-config.sh')

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('16.3'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',

    paths.layer_AAB.gmp / 'usr/local',
    paths.layer_AAB.iconv / 'usr/local',
    paths.layer_AAB.mpc / 'usr/local',
    paths.layer_AAB.mpfr / 'usr/local',
    paths.layer_AAB.python / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      '--host=x86_64-w64-mingw32',
      f'--target={arch}-linux-gnu',
      f'--build={config.build}',
      # prefer static
      '--disable-inprocess-agent',
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-sim',
      '--disable-tui',
      # packages
      '--without-gdbserver',
      '--with-system-gdbinit=/share/gdb/gdbinit',
      *python_flags,
      *cflags_M(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_ABC.gdb)

    gdbinit = layer_ABC.gdb / 'share/gdb/gdbinit'
    with open(gdbinit, 'w') as f:
      f.write('set target-charset UTF-8\n')

    if ver.python:
      ensure(layer_ABC.gdb / 'lib')
      shutil.copy(f'/usr/local/x86_64-w64-mingw32/lib/python.zip', layer_ABC.gdb / 'lib/python.zip')
      with open(layer_ABC.gdb / 'bin/gdb._pth', 'w') as f:
        f.write('../lib/python.zip\n')
      with open(gdbinit, 'a') as f:
        f.write('python\n')
        f.write('from libstdcxx.v6.printers import register_libstdcxx_printers\n')
        f.write('register_libstdcxx_printers(None)\n')
        f.write('end\n')

  create_unprefixed_alias(layer_ABC.gdb, f'{arch}-linux-gnu')

  remove_info_main_menu(layer_ABC.gdb)

  # collision with binutils
  for info_file in ['bfd.info', 'ctf-spec.info', 'sframe-spec.info']:
    os.unlink(layer_ABC.gdb / 'share/info' / info_file)

  license_dir = layer_ABC.gdb / 'share/licenses/gdb'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.gdb / file, license_dir / file)

def build_ABC_toolchain(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _binutils(arch, ver, paths, config)

  _linux_headers(arch, ver, paths, config)

  _glibc(arch, ver, paths, config)

  _gcc(arch, ver, paths, config)

  _gdb(arch, ver, paths, config)
