import logging
import os
from packaging.version import Version
from pathlib import Path
import re
import shutil
import subprocess

from module.fetch import validate_and_download, check_and_extract, patch, patch_done
from module.path import ProjectPaths
from module.profile import BranchProfile

def _autoreconf(path: Path):
  subprocess.run(
    ['autoreconf', '-fi'],
    cwd = path,
    check = True,
  )

def _automake(path: Path):
  subprocess.run(
    ['automake'],
    cwd = path,
    check = True,
  )

def _binutils(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/binutils/{paths.src_arx.binutils.name}'
  validate_and_download(paths.src_arx.binutils, url)
  if check_and_extract(paths.src_dir.binutils, paths.src_arx.binutils):
    v = Version(ver.binutils)

    # Backport
    if v == Version('2.37'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'backport_2.37.patch')
    elif v == Version('2.33.1'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'backport_2.33.1.patch')
    elif v == Version('2.27'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'backport_2.27.patch')

    # Fix path corruption
    if v >= Version('2.43'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'fix-path-corruption_2.43.patch')
    elif v >= Version('2.41'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'fix-path-corruption_2.41.patch')
    elif v >= Version('2.39'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'fix-path-corruption_2.39.patch')

    # Fix elf compress alignment
    if v >= Version('2.32'):
      pass
    elif v >= Version('2.30'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'fix-elf-compress-alignment_2.30.patch')
    elif v >= Version('2.29'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'fix-elf-compress-alignment_2.29.patch')
    elif v >= Version('2.26'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'fix-elf-compress-alignment_2.26.patch')

    # Always enable sysroot
    if v < Version('2.26'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'always-enable-sysroot.patch')

    # Fix musl locale name
    if v < Version('2.29.1'):
      patch(paths.src_dir.binutils, paths.patch_dir / 'binutils' / 'fix-musl-locale-name.patch')

    patch_done(paths.src_dir.binutils)

def _gcc(ver: BranchProfile, paths: ProjectPaths):
  v = Version(ver.gcc)

  is_snapshot = re.search(r'-\d{8}$', ver.gcc)
  if is_snapshot:
    url = f'https://gcc.gnu.org/pub/gcc/snapshots/{ver.gcc}/{paths.src_arx.gcc.name}'
  else:
    url = f'https://ftpmirror.gnu.org/gnu/gcc/gcc-{ver.gcc}/{paths.src_arx.gcc.name}'

  validate_and_download(paths.src_arx.gcc, url)
  if check_and_extract(paths.src_dir.gcc, paths.src_arx.gcc):
    # Backport
    if v.major == 11:
      # - poisoned calloc when building with musl
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'backport_11.patch')
    elif v.major == 10:
      # - mingw define standard PRI macros when building against musl
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'backport_10.patch')
    elif v.major == 9:
      # - mingw define standard PRI macros when building against musl
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'backport_9.patch')
    elif v.major == 8:
      # - gcc fails to find cc1plus if built against ucrt due to a behaviour of `_access`
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'backport_8.patch')
    elif v.major == 7:
      # - someone declared `bool error_p = NULL`, it works until musl 1.2 defines NULL to nullptr
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'backport_7.patch')
    elif v.major == 6:
      # - someone declared `bool error_p = NULL`, it works until musl 1.2 defines NULL to nullptr
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'backport_6.patch')
    elif v.major == 5:
      # - someone declared `bool error_p = NULL`, it works until musl 1.2 defines NULL to nullptr
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'backport_5.patch')

    # Disable default utf8 manifest
    # We patch the CRT init objects, so GCC's manifest should be disabled.
    # But we want no `--disable-win32-utf8-manifest` in configure flags to avoid confusion.
    if v.major >= 13:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'disable-default-utf8-manifest.patch')

    # Fix failure due to language standard evolve
    if v.major < 6:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-lang-std.patch')

    # Fix libc -> libgcc -> libc dependency
    if v.major >= 16:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-libc-libgcc-libc-dep_16.patch')
    elif v.major >= 9:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-libc-libgcc-libc-dep_9.patch')
    elif v.major >= 8:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-libc-libgcc-libc-dep_8.patch')
    else:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-libc-libgcc-libc-dep_5.patch')

    # Fix make variable
    # - gcc 12 use `override CFLAGS +=` to handle PGO build, which breaks workaround for ucrt `access`
    if v.major >= 14:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-make-variable_14.patch')
    elif v.major >= 12:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-make-variable_12.patch')

    # Fix libatomic build
    if v.major < 10:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-libatomic-build.patch')

    # Fix sanitizer dependency of crypt
    if v.major == 13:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-sanitizer-dep.patch')

    # Fix VT sequence
    if v.major >= 12:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-vt-seq_12.patch')
    elif v.major >= 8:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-vt-seq_8.patch')

    # Fix libcpp setlocale
    # libcpp defines `setlocale` if `HAVE_SETLOCALE` not defined, but its configure.ac does not check `setlocale` at all
    patch(paths.src_dir.gcc, paths.patch_dir / 'gcc' / 'fix-libcpp-setlocale.patch')

    # Parser-friendly diagnostics
    po_dir = paths.src_dir.gcc / 'gcc' / 'po'
    po_files = list(po_dir.glob('*.po'))
    subprocess.run([
      'sed',
      '-i', '-E',
      '/^msgid "(error|warning): "/,+1 d',
      *po_files
    ], check = True)

    # x86_64 use `lib` instead of `lib64`
    filepath = paths.src_dir.gcc / 'gcc' / 'config' / 'i386' / 't-linux64'
    content = open(filepath).readlines()
    with open(filepath, 'w') as f:
      for line in content:
        if 'm64=' in line:
          f.write(line.replace('lib64', 'lib'))
        else:
          f.write(line)

    # aarch64 use `lib` instead of `lib64`
    filepath = paths.src_dir.gcc / 'gcc' / 'config' / 'aarch64' / 't-aarch64-linux'
    content = open(filepath).readlines()
    with open(filepath, 'w') as f:
      for line in content:
        if 'mabi.lp64=' in line:
          f.write(line.replace('lib64', 'lib'))
        else:
          f.write(line)

    patch_done(paths.src_dir.gcc)

def _gdb(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/gdb/{paths.src_arx.gdb.name}'
  validate_and_download(paths.src_arx.gdb, url)
  if check_and_extract(paths.src_dir.gdb, paths.src_arx.gdb):
    v = Version(ver.gdb)

    # Backport
    if v.major == 10:
      patch(paths.src_dir.gdb, paths.patch_dir / 'gdb' / 'backport_10.patch')
    elif v == Version('8.3.1'):
      patch(paths.src_dir.gdb, paths.patch_dir / 'gdb' / 'backport_8.3.1.patch')

    # Fix iconv 'CP65001'
    patch(paths.src_dir.gdb, paths.patch_dir / 'gdb' / 'fix-iconv-cp65001.patch')

    # Fix pythondir
    if ver.python:
      patch(paths.src_dir.gdb, paths.patch_dir / 'gdb' / 'fix-pythondir.patch')

    patch_done(paths.src_dir.gdb)

def _glibc(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/glibc/{paths.src_arx.glibc.name}'
  validate_and_download(paths.src_arx.glibc, url)
  if check_and_extract(paths.src_dir.glibc, paths.src_arx.glibc):
    v = Version(ver.glibc)

    # Disable sunrpc
    # glibc wrongly implements host tool `rpcgen` as glibc-only
    # since they finally removed it, we disable it for old versions
    if v < Version('2.26'):
      patch(paths.src_dir.glibc, paths.patch_dir / 'glibc' / 'disable-sunrpc.patch')

    patch_done(paths.src_dir.glibc)

def _gmp(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/gmp/{paths.src_arx.gmp.name}'
  validate_and_download(paths.src_arx.gmp, url)
  check_and_extract(paths.src_dir.gmp, paths.src_arx.gmp)
  patch_done(paths.src_dir.gmp)

def _iconv(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/libiconv/{paths.src_arx.iconv.name}'
  validate_and_download(paths.src_arx.iconv, url)
  check_and_extract(paths.src_dir.iconv, paths.src_arx.iconv)
  patch_done(paths.src_dir.iconv)

def _intl(ver: BranchProfile, paths: ProjectPaths):
  shutil.copytree(
    paths.in_tree_src_tree.intl,
    paths.in_tree_src_dir.intl,
    ignore = shutil.ignore_patterns(
      '.cache',
      '.vscode',
      '.xmake',
      'build',
      'pkg',
      '*.mo',
    ),
    dirs_exist_ok = True,
  )

def _linux(ver: BranchProfile, paths: ProjectPaths):
  v = Version(ver.linux)
  url = f'https://cdn.kernel.org/pub/linux/kernel/v{v.major}.x/{paths.src_arx.linux.name}'
  validate_and_download(paths.src_arx.linux, url)
  check_and_extract(paths.src_dir.linux, paths.src_arx.linux)
  patch_done(paths.src_dir.linux)

def _make(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/make/{paths.src_arx.make.name}'
  validate_and_download(paths.src_arx.make, url)
  if check_and_extract(paths.src_dir.make, paths.src_arx.make):
    v = Version(ver.make)

    # Backport
    if v == Version('4.3'):
      patch(paths.src_dir.make, paths.patch_dir / 'make' / 'backport_4.3.patch')

    # Fix fcntl declaration
    if v == Version('4.3'):
      patch(paths.src_dir.make, paths.patch_dir / 'make' / 'fix-fcntl-decl.patch')

    patch_done(paths.src_dir.make)

def _mingw(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://downloads.sourceforge.net/project/mingw-w64/mingw-w64/mingw-w64-release/{paths.src_arx.mingw.name}'
  validate_and_download(paths.src_arx.mingw, url)
  if check_and_extract(paths.src_dir.mingw, paths.src_arx.mingw):
    v = Version(ver.mingw)

    # CRT: hack console
    # 1. Automatically set console code page to match ACP (especially UTF-8).
    # 2. Set stdio to binary mode to workaround CRT's bugged "double translation".
    #    a. UCRT randomly eats linefeeds when piping on Windows Vista.
    #       Compiling any non-trivial program compiled with '-g3 -pipe'
    #       is likely to fail.
    #    b. MSVCRT, and UCRT prior to 10.0.14393, cannot write multi-byte
    #       characters one-char-by-one-char after set_locale(LC_ALL, "").
    #         int main()
    #         {
    #           setlocale(LC_ALL, "");
    #           for (auto ch : "你好")
    #             fputc(ch, stdout);
    #         }
    #       This is exactly how MinGW-w64's printf and toolchain's NLS work.
    if v.major >= 6:
      patch(paths.src_dir.mingw, paths.patch_dir / 'mingw' / 'hack-console_6.patch')
    else:
      patch(paths.src_dir.mingw, paths.patch_dir / 'mingw' / 'hack-console_4.patch')

    patch_done(paths.src_dir.mingw)

def _mpc(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/mpc/{paths.src_arx.mpc.name}'
  validate_and_download(paths.src_arx.mpc, url)
  check_and_extract(paths.src_dir.mpc, paths.src_arx.mpc)
  patch_done(paths.src_dir.mpc)

def _mpfr(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://ftpmirror.gnu.org/gnu/mpfr/{paths.src_arx.mpfr.name}'
  validate_and_download(paths.src_arx.mpfr, url)
  check_and_extract(paths.src_dir.mpfr, paths.src_arx.mpfr)
  patch_done(paths.src_dir.mpfr)

def _python(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://www.python.org/ftp/python/{ver.python}/{paths.src_arx.python.name}'
  validate_and_download(paths.src_arx.python, url)
  if check_and_extract(paths.src_dir.python, paths.src_arx.python):
    ver = Version(ver.python)

    # Fix static build
    if ver >= Version('3.14'):
      patch(paths.src_dir.python, paths.patch_dir / 'python' / 'fix-static-build.patch')

    # Alternative build system
    os.symlink(paths.src_dir.z, paths.src_dir.python / 'zlib', target_is_directory = True)
    if ver >= Version('3.14'):
      shutil.copy(paths.patch_dir / 'python' / 'xmake_3.14.lua', paths.src_dir.python / 'xmake.lua')
      patch(paths.src_dir.python, paths.patch_dir / 'python' / 'fix-mingw-build_3.14.patch')
    elif ver >= Version('3.13'):
      shutil.copy(paths.patch_dir / 'python' / 'xmake_3.13.lua', paths.src_dir.python / 'xmake.lua')
      patch(paths.src_dir.python, paths.patch_dir / 'python' / 'fix-mingw-build_3.13.patch')
    else:
      shutil.copy(paths.patch_dir / 'python' / 'xmake_3.12.lua', paths.src_dir.python / 'xmake.lua')
      patch(paths.src_dir.python, paths.patch_dir / 'python' / 'fix-mingw-build_3.12.patch')
    shutil.copy(paths.patch_dir / 'python' / 'python-config.sh', paths.src_dir.python / 'python-config.sh')

    patch_done(paths.src_dir.python)

def _xmake(ver: BranchProfile, paths: ProjectPaths):
  release_name = paths.src_arx.xmake.name.replace('xmake-', 'xmake-v')
  url = f'https://github.com/xmake-io/xmake/releases/download/v{ver.xmake}/{release_name}'
  validate_and_download(paths.src_arx.xmake, url)

  if check_and_extract(paths.src_dir.xmake, paths.src_arx.xmake):
    # disable werror
    xmake_lua = paths.src_dir.xmake / 'core/xmake.lua'
    with open(xmake_lua, 'r') as f:
      xmake_lua_content = f.readlines()
    with open(xmake_lua, 'w') as f:
      for line in xmake_lua_content:
        if line.startswith('set_warnings'):
          f.write('set_warnings("all")\n')
        else:
          f.write(line)

    patch_done(paths.src_dir.xmake)

def _z(ver: BranchProfile, paths: ProjectPaths):
  url = f'https://github.com/madler/zlib/releases/download/v{ver.z}/{paths.src_arx.z.name}'
  validate_and_download(paths.src_arx.z, url)
  check_and_extract(paths.src_dir.z, paths.src_arx.z)
  patch_done(paths.src_dir.z)

def prepare_source(ver: BranchProfile, paths: ProjectPaths):
  _binutils(ver, paths)
  _gcc(ver, paths)
  _gdb(ver, paths)
  _glibc(ver, paths)
  _gmp(ver, paths)
  _iconv(ver, paths)
  _intl(ver, paths)
  _linux(ver, paths)
  _make(ver, paths)
  _mingw(ver, paths)
  _mpc(ver, paths)
  _mpfr(ver, paths)
  if ver.python:
    _python(ver, paths)
  _xmake(ver, paths)
  _z(ver, paths)
