import argparse
from packaging.version import Version
import shutil
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import BranchProfile
from module.util import ensure, overlayfs_ro
from module.util import cflags_A, cflags_B, configure, make_custom, make_default, make_destdir_install
from module.util import xmake_build, xmake_config, xmake_install

def _binutils(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.binutils / 'build-AAB'
  ensure(build_dir)
  configure(build_dir, [
    '--prefix=/usr/local',
    '--target=x86_64-w64-mingw32',
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
  make_destdir_install(build_dir, paths.layer_AAB.binutils)

def _headers(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mingw / 'mingw-w64-headers' / 'build-AAB'
  ensure(build_dir)

  if ver.win32_winnt >= 0x0A00:
    crt = 'ucrt'
  else:
    crt = 'msvcrt'

  configure(build_dir, [
    '--prefix=/usr/local/x86_64-w64-mingw32',
    '--host=x86_64-w64-mingw32',
    f'--build={config.build}',
    f'--with-default-msvcrt={crt}',
    f'--with-default-win32-winnt=0x{ver.win32_winnt:04X}',
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_AAB.headers)
  yield

  include_dir = paths.layer_AAB.headers / 'usr/local/x86_64-w64-mingw32/include'
  for dummy_header in ['pthread_signal.h', 'pthread_time.h', 'pthread_unistd.h']:
    (include_dir / dummy_header).unlink()
  yield

def _gcc(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  build_dir = paths.src_dir.gcc / 'build-AAB'
  ensure(build_dir)

  config_flags = []
  c_extra = []
  cxx_extra = []

  if v.major >= 7:
    config_flags.append('--with-gcc-major-version-only')
  else:
    c_extra.append('-std=gnu89')
    cxx_extra.append('-std=gnu++98')

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
    paths.layer_AAA.mpc / 'usr/local',
    paths.layer_AAA.mpfr / 'usr/local',

    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local',
      '--libexecdir=/usr/local/lib',
      '--target=x86_64-w64-mingw32',
      f'--build={config.build}',
        # prefer static
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-bootstrap',
      '--enable-checking=release',
      '--enable-host-pie',
      '--enable-languages=c,c++',
      '--disable-libgomp',
      '--disable-libmpx',
      '--disable-multilib',
      '--disable-nls',
      '--enable-threads=posix',
      # packages
      '--without-libcc1',
      *config_flags,
      *cflags_A(
        c_extra = c_extra,
        cxx_extra = cxx_extra,
      ),
      *cflags_B('_FOR_TARGET'),
    ])

    make_custom(build_dir, ['all-gcc'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={paths.layer_AAB.gcc}',
      'install-gcc',
    ], jobs = 1)
  yield

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
    paths.layer_AAA.mpc / 'usr/local',
    paths.layer_AAA.mpfr / 'usr/local',

    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.gcc)
  yield

def _crt(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.mingw / 'mingw-w64-crt' / 'build-AAB'
  ensure(build_dir)

  if ver.win32_winnt >= 0x0A00:
    crt = 'ucrt'
  else:
    crt = 'msvcrt'

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-w64-mingw32',
      '--host=x86_64-w64-mingw32',
      f'--build={config.build}',
      f'--with-default-msvcrt={crt}',
      f'--with-default-win32-winnt=0x{ver.win32_winnt:04X}',
      '--enable-lib64',
      '--disable-lib32',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.crt)

    # The future belongs to UTF-8.
    # Piping is used so widely in GNU toolchain that we have to apply UTF-8 manifest to all programs.
    subprocess.run([
      'x86_64-w64-mingw32-windres',
      '-O', 'coff',
      paths.utf8_src_dir / 'utf8-manifest.rc',
      '-o', build_dir / 'utf8-manifest.o',
    ], check = True)
    for crt_object in ['crt1.o', 'crt1u.o', 'crt2.o', 'crt2u.o']:
      subprocess.run([
        'x86_64-w64-mingw32-gcc' if v_gcc.major >= 9 else 'x86_64-w64-mingw32-ld',
        '-r',
        build_dir / 'lib64' / crt_object,
        build_dir / 'utf8-manifest.o',
        '-o', paths.layer_AAB.crt / 'usr/local/x86_64-w64-mingw32/lib' / crt_object,
      ], check = True)

def _winpthreads(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mingw / 'mingw-w64-libraries' / 'winpthreads' / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-w64-mingw32',
      '--host=x86_64-w64-mingw32',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)

    # as the basis of gthread interface, it should be considered as part of gcc
    make_destdir_install(build_dir, paths.layer_AAB.gcc)

def build_AAB_compiler(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _binutils(ver, paths, config)

  headers = _headers(ver, paths, config)
  headers.__next__()

  gcc = _gcc(ver, paths, config)
  gcc.__next__()

  _crt(ver, paths, config)

  _winpthreads(ver, paths, config)
  headers.__next__()

  gcc.__next__()

def _gmp(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gmp)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.gmp / 'build-AAB'
  ensure(build_dir)

  c_extra = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('6.4.0'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-w64-mingw32',
      '--host=x86_64-w64-mingw32',
      f'--build={config.build}',
      '--disable-assembly',
      '--enable-static',
      '--disable-shared',
      *cflags_B(c_extra = c_extra),
      # To determine build system compiler, the configure script will firstly try host
      # compiler (i.e. *-w64-mingw32-gcc) and check whether the output is executable
      # (and fallback to cc otherwise). However, in WSL or Linux with Wine configured,
      # the check passes and thus *-w64-mingw32-gcc is detected as build system compiler.
      # Here we force the build system compiler to be gcc.
      'CC_FOR_BUILD=gcc',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.gmp)

def _mpfr(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mpfr / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',

    paths.layer_AAB.gmp / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-w64-mingw32',
      '--host=x86_64-w64-mingw32',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.mpfr)

def _mpc(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mpc / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',

    paths.layer_AAB.gmp / 'usr/local',
    paths.layer_AAB.mpfr / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-w64-mingw32',
      '--host=x86_64-w64-mingw32',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.mpc)

def _iconv(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.iconv)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.iconv / 'build-AAB'
  ensure(build_dir)

  triplet_args = ['--host=x86_64-w64-mingw32']
  c_extra = []

  # libiconv 1.14 does not recognize 'x86_64-alpine-linux-musl'
  if v >= Version('1.15'):
    triplet_args.append(f'--build={config.build}')

  # GCC 15 defaults to C23
  if v_gcc.major >= 15 and v < Version('1.18'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local/x86_64-w64-mingw32',
      *triplet_args,
      '--disable-nls',
      '--enable-static',
      '--disable-shared',
      *cflags_B(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.iconv)

def _intl(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    v_gcc = Version(ver.gcc)
    src_dir = paths.in_tree_src_dir.intl

    config_flags = []

    if v_gcc.major < 6:
      config_flags.append('--nested-ns=n')

    xmake_config(src_dir, [
      '--plat=mingw',
      '--arch=x86_64',
      *config_flags,
    ])
    xmake_build(src_dir, config.jobs)

    install_dir = paths.layer_AAB.intl / 'usr/local/x86_64-w64-mingw32'
    xmake_install(src_dir, install_dir)

def _python(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v_gcc = Version(ver.gcc)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.python / 'usr/local',

    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.crt / 'usr/local',
    paths.layer_AAB.gcc / 'usr/local',
    paths.layer_AAB.headers / 'usr/local',
  ]):
    src_dir = paths.src_dir.python

    xmake_config(src_dir, [
      '--plat=mingw',
      '--arch=x86_64',
    ])
    xmake_build(src_dir, config.jobs)

    install_dir = paths.layer_AAB.python / 'usr/local/x86_64-w64-mingw32'
    xmake_install(src_dir, install_dir, ['pythoncore'])

    stdlib_package_dir = src_dir / 'build/stdlib-package'
    ensure(stdlib_package_dir)
    xmake_install(src_dir, stdlib_package_dir, ['stdlib'])

    python_lib = stdlib_package_dir / 'Lib'
    if v_gcc.major >= 7:
      gcc_python_dir = f'/usr/local/share/gcc-{v_gcc.major}/python'
    else:
      gcc_python_dir = f'/usr/local/share/gcc-{ver.gcc}/python'
    shutil.copytree(gcc_python_dir, python_lib, dirs_exist_ok = True)
    subprocess.run([
      'python3', '-m', 'compileall',
      '-b',
      '-o', '2',
      '.',
    ], check = True, cwd = python_lib)

    python_lib_zip = install_dir / 'lib/python.zip'
    if python_lib_zip.exists():
      python_lib_zip.unlink()
    subprocess.run([
      '7z', 'a', '-tzip',
      '-mx0',  # no compression, reduce final size
      python_lib_zip,
      '*', '-xr!__pycache__', '-xr!*.py',
    ], check = True, cwd = python_lib)

def build_AAB_library(ver: BranchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmp(ver, paths, config)

  _mpfr(ver, paths, config)

  _mpc(ver, paths, config)

  _iconv(ver, paths, config)

  _intl(ver, paths, config)

  if ver.python:
    _python(ver, paths, config)
  else:
    ensure(paths.layer_AAB.python / 'usr/local')
