import argparse
from packaging.version import Version
import shutil
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import add_objects_to_static_lib, common_MMC_layers, ensure, extract_system_components, overlayfs_ro
from module.util import cflags_A, cflags_B, configure, make_custom, make_default, make_destdir_install
from module.util import xmake_build, xmake_config, xmake_install

def _binutils(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.binutils / 'build-MMC'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_MMC.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local',
      '--target=x86_64-pc-cygwin',
      f'--build={config.build}',
      # prefer static
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-install-libbfd',
      '--disable-multilib',
      '--disable-nls',
      '--disable-werror',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.binutils)

def _mingw_headers(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mingw / 'mingw-w64-headers' / 'build-MMC'
  ensure(build_dir)

  configure(build_dir, [
    '--prefix=/usr/local/x86_64-pc-cygwin',
    '--host=x86_64-pc-cygwin',
    f'--build={config.build}',
    '--enable-w32api',
    f'--with-default-win32-winnt=0x{ver.win32_winnt:04X}',
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_MMC.mingw_headers)

def _cygwin_bootstrap(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.cygwin)

  if v.major == 3:
    bootstrap_version = '3.0.7-1'
  elif v.major == 2:
    bootstrap_version = '2.0.4-1'
  elif v.major == 1:
    bootstrap_version = '1.7.35-1'
  else:
    raise NotImplementedError(f'cygwin version {v} not supported')

  boots_bin_pkg = paths.root_dir / f'support/bootstrap/cygwin-devel-{bootstrap_version}-x86_64.tar.xz'
  prefix = paths.layer_MMC.bootstrap / 'usr/local/x86_64-pc-cygwin'
  ensure(prefix)

  subprocess.run([
    'bsdtar', '-xf', boots_bin_pkg, '--no-same-owner', '--strip-components=1',
  ], cwd = prefix, check = True)

  # workaround GCC checking for inhibit_libc
  ensure(prefix / 'sys-include')
  shutil.copy(prefix / 'include/stdio.h', prefix / 'sys-include/stdio.h')

def _gcc_1(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  build_dir = paths.src_dir.gcc / 'build-MMC'
  ensure(build_dir)

  config_flags = []
  c_extra = []
  cxx_extra = []

  if v.major >= 7:
    config_flags.append('--with-gcc-major-version-only')
  else:
    c_extra.append('-std=gnu89')
    cxx_extra.append('-std=gnu++98')

  if v.major >= 6:
    config_flags.append('--enable-host-pie')

  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.gmp / 'usr/local',
    paths.layer_MMM.mpc / 'usr/local',
    paths.layer_MMM.mpfr / 'usr/local',
    paths.layer_MMC.zlib / 'usr/local',

    paths.layer_MMC.binutils / 'usr/local',
    paths.layer_MMC.bootstrap / 'usr/local',
    paths.layer_MMC.mingw_headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local',
      '--libexecdir=/usr/local/lib',
      '--target=x86_64-pc-cygwin',
      f'--build={config.build}',
        # prefer static
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-bootstrap',
      '--enable-checking=release',
      '--enable-languages=c,c++',
      '--disable-libgomp',
      '--disable-libmpx',
      '--disable-multilib',
      '--disable-nls',
      '--enable-threads=posix',
      # packages
      '--without-libcc1',
      '--with-system-zlib',
      *config_flags,
      *cflags_A(
        c_extra = c_extra,
        cxx_extra = cxx_extra,
      ),
      *cflags_B('_FOR_TARGET'),
    ])

    make_custom(build_dir, ['all-gcc'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={paths.layer_MMC.gcc}',
      'install-gcc',
    ], jobs = 1)

def _gcc_2(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gcc / 'build-MMC'

  with overlayfs_ro('/usr/local', [
    paths.layer_MMC.binutils / 'usr/local',
    paths.layer_MMC.bootstrap / 'usr/local',
    paths.layer_MMC.gcc / 'usr/local',
    paths.layer_MMC.mingw_crt / 'usr/local',
    paths.layer_MMC.mingw_headers / 'usr/local',
  ]):
    make_custom(build_dir, [
      'all-target-libgcc',
      'all-target-libstdc++-v3',
    ], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={paths.layer_MMC.gcc}',
      'install-target-libgcc',
      'install-target-libstdc++-v3',
    ], jobs = 1)

def _gcc_3(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gcc / 'build-MMC'

  with overlayfs_ro('/usr/local', [
    paths.layer_MMC.binutils / 'usr/local',
    paths.layer_MMC.cygwin / 'usr/local',
    paths.layer_MMC.gcc / 'usr/local',
    paths.layer_MMC.mingw_crt / 'usr/local',
    paths.layer_MMC.mingw_headers / 'usr/local',
  ]):
    make_custom(build_dir, ['all-target'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={paths.layer_MMC.gcc}',
      'install-target',
    ], jobs = 1)

def _mingw_crt(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mingw / 'mingw-w64-crt' / 'build-MMC'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_MMC.binutils / 'usr/local',
    paths.layer_MMC.bootstrap / 'usr/local',
    paths.layer_MMC.gcc / 'usr/local',
    paths.layer_MMC.mingw_headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-pc-cygwin',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      '--disable-lib32',
      '--enable-lib64',
      '--enable-w32api',
      f'--with-default-win32-winnt=0x{ver.win32_winnt:04X}',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.mingw_crt)

def _cygwin(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.cygwin)

  # workaround: winsup/cygwin/Makefile.am
  #   install-headers:
  #     cd $(srcdir)/include; ... ; $(MKDIR_P)
  # if build in subdir, $(MKDIR_P) has one more level of '..'
  # so we build it at same level to avoid this
  build_dir = paths.src_dir.cygwin.parent / 'cygwin-build-MMC'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_MMC.binutils / 'usr/local',
    paths.layer_MMC.bootstrap / 'usr/local',
    paths.layer_MMC.gcc / 'usr/local',
    paths.layer_MMC.mingw_headers / 'usr/local',
    paths.layer_MMC.mingw_crt / 'usr/local',
  ]):
    subprocess.run([
      './autogen.sh'
    ], cwd = paths.src_dir.cygwin / 'winsup', check = True)
    subprocess.run([
      paths.src_dir.cygwin / 'configure',
      '--prefix=/usr/local',
      '--target=x86_64-pc-cygwin',
      f'--host={config.build}',
      f'--build={config.build}',
      '--disable-doc',
      '--disable-dumper',
      '--with-cross-bootstrap',
      *cflags_A(),
      *cflags_B('_FOR_TARGET',
        # workaround winsup hard-coded search path
        cxx_extra = ['-L/usr/local/x86_64-pc-cygwin/lib/w32api'],
      ),
    ], cwd = build_dir, check = True)
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.cygwin)

  base_prefix = paths.layer_MMC.cygwin / 'usr/local'
  sys_prefix = paths.layer_MMC.cygwin_sys / 'usr/local'

  extract_system_components(
    base_prefix,
    sys_prefix,
    include_dirs = ['bin', 'sbin', 'etc', 'share'],
  )

def build_MMC_compiler(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _binutils(ver, paths, config)
  _mingw_headers(ver, paths, config)
  _cygwin_bootstrap(ver, paths, config)
  _gcc_1(ver, paths, config)
  _mingw_crt(ver, paths, config)
  _gcc_2(ver, paths, config)
  _cygwin(ver, paths, config)
  _gcc_3(ver, paths, config)

def _gmp(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gmp)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.gmp / 'build-MMC'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('6.4.0'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', common_MMC_layers(paths)):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-pc-cygwin',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      '--disable-assembly',
      '--enable-static',
      '--disable-shared',
      *cflags_B(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.gmp)

def _mpfr(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mpfr / 'build-MMC'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    *common_MMC_layers(paths),

    paths.layer_MMC.gmp / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-pc-cygwin',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.mpfr)

def _mpc(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mpc / 'build-MMC'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    *common_MMC_layers(paths),

    paths.layer_MMC.gmp / 'usr/local',
    paths.layer_MMC.mpfr / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-pc-cygwin',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.mpc)

def _iconv(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.iconv)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.iconv / 'build-MMC'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('1.18'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', common_MMC_layers(paths)):
    configure(build_dir, [
      '--prefix=/usr/local',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      '--disable-nls',
      '--enable-static',
      '--disable-shared',
      *cflags_B(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.iconv)

def _intl(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gettext / 'gettext-runtime' / 'build-MMC'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', common_MMC_layers(paths)):
    configure(build_dir, [
      '--prefix=/usr/local',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.intl)

def _zlib_net(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.zlib_net / 'build-MMC'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', common_MMC_layers(paths)):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-pc-cygwin',
      '--static',
    ])
    make_custom(build_dir, [
      'CC=x86_64-pc-cygwin-gcc',
      'all',
    ], config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.zlib)

def _python(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.python)
  v_gcc = Version(ver.gcc)

  build_dir = paths.src_dir.python / 'build-MMC'
  ensure(build_dir)

  abi_ver = f'{v.major}.{v.minor}'
  build_python = f'/usr/local/bin/python{abi_ver}'

  with overlayfs_ro('/usr/local', [
    paths.layer_MMM.python / 'usr/local',

    *common_MMC_layers(paths),

    paths.layer_MMC.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/x86_64-pc-cygwin',
      '--host=x86_64-pc-cygwin',
      f'--build={config.build}',
      # static
      '--disable-shared',
      'MODULE_BUILDTYPE=static',
      # features
      '--enable-ipv6',
      '--disable-test-modules',
      # packages
      f'--with-build-python={build_python}',
      '--without-ensurepip',
      '--with-suffix=.exe',
      *cflags_A(),
      'ac_cv_file__dev_ptc=no',
      'ac_cv_file__dev_ptmx=yes',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_MMC.python)

    shutil.copy(paths.root_dir / 'support/gdb/gdb-python.sh', paths.layer_MMC.python / f'usr/local/x86_64-pc-cygwin/bin/gdb-python.sh')

    dest_lib_dir = paths.layer_MMC.python / f'usr/local/x86_64-pc-cygwin/lib'
    python_lib_dir = dest_lib_dir / f'python{abi_ver}'

    libpython_a = dest_lib_dir / f'libpython{abi_ver}.a'
    hacl_sha2_obj = build_dir / 'Modules/_hacl/Hacl_Hash_SHA2.o'
    add_objects_to_static_lib(f'x86_64-pc-cygwin-ar', libpython_a, [hacl_sha2_obj])

    config_dir = python_lib_dir / f'config-{abi_ver}'
    shutil.rmtree(config_dir)

    subprocess.run([
      build_python, '-m', 'compileall',
      '-b',
      '-o', '2',
      '.',
    ], check = True, cwd = python_lib_dir)

def build_MMC_library(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmp(ver, paths, config)
  _mpfr(ver, paths, config)
  _mpc(ver, paths, config)
  _iconv(ver, paths, config)
  _intl(ver, paths, config)
  _zlib_net(ver, paths, config)
  _python(ver, paths, config)
