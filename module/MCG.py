import argparse
import glob
import os
from packaging.version import Version
import shutil
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import common_MMC_layers, common_MMG_layers, create_unprefixed_alias, ensure, extract_system_components, fix_limits_h, overlayfs_ro, remove_info_main_menu
from module.util import cflags_B, cflags_C, configure, make_custom, make_default, make_destdir_install

def _binutils(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  layer_MCG = paths.layer_MCG(arch)
  build_dir = paths.src_dir.binutils / f'build-MCG-{arch}'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    *common_MMC_layers(paths),

    paths.layer_MMC.intl / 'usr/local',
    paths.layer_MMC.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      '--host=x86_64-pc-cygwin',
      f'--target={arch}-linux-gnu',
      f'--build={config.build}',
      # workaround: bfd plugin 'dep' should be built as shared object
      '--enable-shared',
      '--enable-static',
      # features
      '--disable-install-libbfd',
      '--disable-multilib',
      '--enable-nls',
      # packages
      '--with-system-zlib',
      *cflags_B(lto = False),
      'AR=x86_64-pc-cygwin-gcc-ar',
      'RANLIB=x86_64-pc-cygwin-gcc-ranlib',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MCG.binutils)

  create_unprefixed_alias(layer_MCG.binutils, f'{arch}-linux-gnu')

  remove_info_main_menu(layer_MCG.binutils)

  license_dir = layer_MCG.binutils / 'share/licenses/binutils'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.binutils / file, license_dir / file)

def _linux_headers(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.linux)

  KARCH_MAP = {
    'aarch64': 'arm64',
    'x86_64': 'x86',
  }

  layer_MCG = paths.layer_MCG(arch)
  prefix = layer_MCG.linux / f'{arch}-linux-gnu'

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

  license_dir = layer_MCG.linux / 'share/licenses/linux'
  ensure(license_dir)
  shutil.copy(paths.src_dir.linux / 'COPYING', license_dir / 'COPYING')
  if v >= Version('4.19'):
    shutil.copy(paths.src_dir.linux / 'LICENSES/preferred/GPL-2.0', license_dir / 'GPL-2.0')
    shutil.copy(paths.src_dir.linux / 'LICENSES/exceptions/Linux-syscall-note', license_dir / 'Linux-syscall-note')

def _glibc(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.glibc)
  layer_MCG = paths.layer_MCG(arch)
  build_dir = paths.src_dir.glibc / f'build-MCG-{arch}'
  ensure(build_dir)

  destdir = layer_MCG.glibc / f'{arch}-linux-gnu'

  with overlayfs_ro('/usr/local', [
    # glibc prior to 2.31 can not be built with make 4.4 (infinite recursion)
    # upstream accidentally fixed it, cherry-pick seems very hard
    # the workaround is to build with make at that time
    # ref. https://github.com/crosstool-ng/crosstool-ng/issues/1932#issuecomment-1528139734
    paths.layer_MMM.make / 'usr/local',

    *common_MMG_layers(arch, paths),
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
      *cflags_C(),
      # disable C++ to avoid -lgcc_s in test links-dso-program
      # which is not supported by static compiler
      'CXX=false',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, destdir)

  sys_prefix = layer_MCG.glibc_sys / f'{arch}-linux-gnu'

  # ... and then extract the dynamic library (and other stuff)
  sys_dirs = ['bin', 'etc', 'lib/gconv', 'libexec', 'sbin', 'share', 'var']
  # not sure since 2.19 or 2.20
  if v >= Version('2.20'):
    sys_dirs.append('lib/audit')

  extract_system_components(
    destdir,
    sys_prefix,
    lib_patterns = ['lib/*.so*'],
    include_dirs = sys_dirs,
  )

  # fix libm.a reference path
  if (arch == 'x86_64' and v >= Version('2.25')) or (arch == 'aarch64' and v >= Version('2.38')):
    libm_content = open(f'{destdir}/lib/libm.a', 'r').read()
    with open(f'{destdir}/lib/libm.a', 'w') as f:
      f.write(libm_content.replace('/lib/', './'))

  license_dir = layer_MCG.glibc / 'share/licenses/glibc'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING.LIB', 'LICENSES']:
    shutil.copy(paths.src_dir.glibc / file, license_dir / file)

def _gcc(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  layer_MCG = paths.layer_MCG(arch)
  build_dir = paths.src_dir.gcc / f'build-MCG-{arch}'
  ensure(build_dir)

  libexec_target = layer_MCG.gcc / f'lib/gcc/{arch}-linux-gnu'

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
    *common_MMC_layers(paths),

    paths.layer_MMC.gmp / 'usr/local',
    paths.layer_MMC.intl / 'usr/local',
    paths.layer_MMC.mpc / 'usr/local',
    paths.layer_MMC.mpfr / 'usr/local',
    paths.layer_MMC.zlib / 'usr/local',

    *common_MMG_layers(arch, paths),
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--libexecdir=/lib',
      '--host=x86_64-pc-cygwin',
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
      '--with-system-zlib',
      *config_flags,
      *cflags_B(lto = False),
      *cflags_C('_FOR_TARGET'),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MCG.gcc)
    fix_limits_h(limits_h, paths.src_dir.gcc)

  create_unprefixed_alias(layer_MCG.gcc, f'{arch}-linux-gnu')

  remove_info_main_menu(layer_MCG.gcc)

  license_dir = layer_MCG.gcc / 'share/licenses/gcc'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.RUNTIME', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.gcc / file, license_dir / file)

def _gdb(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gdb)
  v_gcc = Version(ver.gcc)
  v_python = Version(ver.python)

  layer_MCG = paths.layer_MCG(arch)
  build_dir = paths.src_dir.gdb / f'build-MCG-{arch}'
  ensure(build_dir)

  python_flags = []
  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v.major < 17:
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    *common_MMC_layers(paths),

    paths.layer_MMC.gmp / 'usr/local',
    paths.layer_MMC.iconv / 'usr/local',
    paths.layer_MMC.mpc / 'usr/local',
    paths.layer_MMC.mpfr / 'usr/local',
    paths.layer_MMC.python / 'usr/local',
    paths.layer_MMC.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      '--host=x86_64-pc-cygwin',
      f'--target={arch}-linux-gnu',
      f'--build={config.build}',
      # prefer static
      '--disable-inprocess-agent',
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-nls',
      '--disable-sim',
      '--disable-tui',
      # packages
      '--without-gdbserver',
      '--with-python=/usr/local/x86_64-pc-cygwin/bin/gdb-python.sh',
      '--with-system-gdbinit=/share/gdb/gdbinit',
      '--with-system-zlib',
      *python_flags,
      *cflags_B(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, layer_MCG.gdb)

    gdbinit = layer_MCG.gdb / 'share/gdb/gdbinit'
    ensure(layer_MCG.gdb / 'lib')
    with open(gdbinit, 'w') as f:
      f.write('python\n')
      f.write('from libstdcxx.v6.printers import register_libstdcxx_printers\n')
      f.write('register_libstdcxx_printers(None)\n')
      f.write('end\n')

    # python standard library
    python_abi_ver = f'{v_python.major}.{v_python.minor}'
    shutil.copytree(
      f'/usr/local/x86_64-pc-cygwin/lib/python{python_abi_ver}',
      layer_MCG.gdb / f'lib/python{python_abi_ver}',
      dirs_exist_ok = True,
      ignore = shutil.ignore_patterns(
        '__pycache__',
        '*.py',
      ),
    )

    # libstdc++ pretty printer
    gcc_python_dir = f'/usr/local/share/gcc-{v_gcc.major}/python'
    gdb_python_dir = layer_MCG.gdb / 'share/gdb/python'
    build_python = f'/usr/local/bin/python{python_abi_ver}'
    shutil.copytree(gcc_python_dir, gdb_python_dir, dirs_exist_ok = True)
    subprocess.run([
      build_python, '-m', 'compileall',
      '-o', '0',
      '-o', '1',
      '-o', '2',
      '.',
    ], check = True, cwd = gdb_python_dir)

  create_unprefixed_alias(layer_MCG.gdb, f'{arch}-linux-gnu')

  remove_info_main_menu(layer_MCG.gdb)

  if v.major >= 14:
    # not sure 14 or 13
    binutils_collision_files = ['bfd.info', 'ctf-spec.info', 'sframe-spec.info']
  elif v.major >= 12:
    binutils_collision_files = ['bfd.info', 'ctf-spec.info']
  else:
    binutils_collision_files = ['bfd.info']

  for info_file in binutils_collision_files:
    os.unlink(layer_MCG.gdb / 'share/info' / info_file)

  license_dir = layer_MCG.gdb / 'share/licenses/gdb'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.gdb / file, license_dir / file)

def build_MCG_toolchain(arch: str, ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _binutils(arch, ver, paths, config)
  _linux_headers(arch, ver, paths, config)
  _glibc(arch, ver, paths, config)
  _gcc(arch, ver, paths, config)
  _gdb(arch, ver, paths, config)
