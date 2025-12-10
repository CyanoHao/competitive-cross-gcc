import argparse
from packaging.version import Version
from pathlib import Path
from typing import Callable, NamedTuple, Optional

from module.profile import BranchProfile

class SourcePaths(NamedTuple):
  binutils: Path
  gcc: Path
  gdb: Path
  glibc: Path
  gmp: Path
  iconv: Path
  linux: Path
  make: Path
  mingw: Path
  mpc: Path
  mpfr: Path
  python: Optional[Path]
  xmake: Path
  z: Path

class InTreeSourcePaths(NamedTuple):
  intl: Path

class LayerPathsAAA(NamedTuple):
  prefix: Path

  gmp: Path
  mpc: Path
  mpfr: Path
  z: Path

  make: Path
  python: Path
  xmake: Path

class LayerPathsAAB(NamedTuple):
  prefix: Path

  binutils: Path
  crt: Path
  gcc: Path
  headers: Path

  gmp: Path
  iconv: Path
  intl: Path
  mpc: Path
  mpfr: Path
  python: Path

class LayerPathsABB(NamedTuple):
  prefix: Path

  make: Path
  xmake: Path

class LayerPathsAAC(NamedTuple):
  prefix: Path

  binutils: Path
  gcc: Path
  glibc: Path
  linux: Path

  gmp: Path
  mpc: Path
  mpfr: Path

class LayerPathsABC(NamedTuple):
  prefix: Path

  binutils: Path
  gcc: Path
  gdb: Path
  glibc: Path
  linux: Path

class LayerPathsACC(NamedTuple):
  prefix: Path

  gdb: Path

class ProjectPaths:
  root_dir: Path

  assets_dir: Path
  dist_dir: Path
  patch_dir: Path

  linux_pkg: Callable[[str], Path]
  xmake_pkg: Path
  cross_pkg: Path

  # build phase

  utf8_src_dir: Path
  build_dir: Path
  layer_dir: Path
  linux_pkg_dir: Callable[[str], Path]
  xmake_pkg_dir: Path

  src_dir: SourcePaths
  src_arx: SourcePaths

  in_tree_src_dir: InTreeSourcePaths
  in_tree_src_tree: InTreeSourcePaths

  layer_AAA: LayerPathsAAA
  layer_AAB: LayerPathsAAB
  layer_ABB: LayerPathsABB
  layer_AAC: Callable[[str], LayerPathsAAC]
  layer_ABC: Callable[[str], LayerPathsABC]
  layer_ACC: Callable[[str], LayerPathsACC]

  # test phase

  test_dir: Path
  test_src_dir: Path

  test_linux_dir: Callable[[str], Path]
  test_xmake_dir: Path

  test_chimaera_src_dir: Path
  test_chimaera_exe: Path

  def __init__(
    self,
    config: argparse.Namespace,
    ver: BranchProfile,
  ):
    self.root_dir = Path.cwd()

    self.assets_dir = self.root_dir / 'assets'
    self.dist_dir = self.root_dir / 'dist'
    self.patch_dir = self.root_dir / 'patch'

    GLIBC_LD_NAME_MAP = {
      'aarch64': 'linux-aarch64',
      'x86_64': 'linux-x86-64',
    }

    self.linux_pkg = lambda arch: self.dist_dir / f'gcc-{GLIBC_LD_NAME_MAP[arch]}-{ver.gcc}-r{ver.rev}.tar.zst'
    self.xmake_pkg = self.dist_dir / f'xmake-mingw64-{ver.gcc}-r{ver.rev}.tar.zst'
    self.cross_pkg = self.dist_dir / f'gcc-x-{ver.gcc}-r{ver.rev}.tar.zst'

    # build phase

    self.utf8_src_dir = self.root_dir / 'support/utf8'
    self.build_dir = Path(f'/tmp/build/gcc-{config.branch}')
    self.layer_dir = Path(f'/tmp/layer/gcc-{config.branch}')
    self.linux_pkg_dir = lambda arch: Path(f'/tmp/pkg/gcc-{GLIBC_LD_NAME_MAP[arch]}-{config.branch}')
    self.xmake_pkg_dir = Path(f'/tmp/pkg/xmake-mingw64-{config.branch}')

    src_name = SourcePaths(
      binutils = f'binutils-{ver.binutils}',
      gcc = f'gcc-{ver.gcc}',
      gdb = f'gdb-{ver.gdb}',
      glibc = f'glibc-{ver.glibc}',
      gmp = f'gmp-{ver.gmp}',
      iconv = f'libiconv-{ver.iconv}',
      linux = f'linux-{ver.linux}',
      make = f'make-{ver.make}',
      mingw = f'mingw-w64-v{ver.mingw}',
      mpc = f'mpc-{ver.mpc}',
      mpfr = f'mpfr-{ver.mpfr}',
      python = f'Python-{ver.python}' if ver.python else None,
      xmake = f'xmake-{ver.xmake}',
      z = f'zlib-{ver.z}',
    )

    self.src_dir = SourcePaths(
      binutils = self.build_dir / src_name.binutils,
      gcc = self.build_dir / src_name.gcc,
      gdb = self.build_dir / src_name.gdb,
      glibc = self.build_dir / src_name.glibc,
      gmp = self.build_dir / src_name.gmp,
      iconv = self.build_dir / src_name.iconv,
      linux = self.build_dir / src_name.linux,
      make = self.build_dir / src_name.make,
      mingw = self.build_dir / src_name.mingw,
      mpc = self.build_dir / src_name.mpc,
      mpfr = self.build_dir / src_name.mpfr,
      python = self.build_dir / src_name.python if src_name.python else None,
      xmake = self.build_dir / src_name.xmake,
      z = self.build_dir / src_name.z,
    )

    self.src_arx = SourcePaths(
      binutils = self.assets_dir / f'{src_name.binutils}.tar.zst'
        if Version(ver.binutils) >= Version('2.43')
        else self.assets_dir / f'{src_name.binutils}.tar.xz'
          if Version(ver.binutils) >= Version('2.28.1')
          else self.assets_dir / f'{src_name.binutils}.tar.bz2',
      gcc = self.assets_dir / f'{src_name.gcc}.tar.xz'
        if Version(ver.gcc).major >= 5
        else self.assets_dir / f'{src_name.gcc}.tar.bz2',
      gdb = self.assets_dir / f'{src_name.gdb}.tar.xz'
        if Version(ver.gdb) >= Version('7.8')
        else self.assets_dir / f'{src_name.gdb}.tar.bz2',
      glibc = self.assets_dir / f'{src_name.glibc}.tar.xz',
      gmp = self.assets_dir / f'{src_name.gmp}.tar.zst'
        if Version(ver.gmp) >= Version('6.2.0')
        else self.assets_dir / f'{src_name.gmp}.tar.xz',
      iconv = self.assets_dir / f'{src_name.iconv}.tar.gz',
      linux = self.assets_dir / f'{src_name.linux}.tar.xz',
      make = self.assets_dir / f'{src_name.make}.tar.lz'
        if Version(ver.make) >= Version('4.3')
        else self.assets_dir / f'{src_name.make}.tar.bz2',
      mingw = self.assets_dir / f'{src_name.mingw}.tar.bz2',
      mpc = self.assets_dir / f'{src_name.mpc}.tar.gz',
      mpfr = self.assets_dir / f'{src_name.mpfr}.tar.xz',
      python = self.assets_dir / f'{src_name.python}.tar.xz' if src_name.python else None,
      xmake = self.assets_dir / f'{src_name.xmake}.tar.gz',
      z = self.assets_dir / f'{src_name.z}.tar.xz',
    )

    self.in_tree_src_dir = InTreeSourcePaths(
      intl = self.build_dir / 'intl',
    )

    self.in_tree_src_tree = InTreeSourcePaths(
      intl = self.root_dir / 'support/intl',
    )

    layer_AAA_prefix = self.layer_dir / 'AAA'
    self.layer_AAA = LayerPathsAAA(
      prefix = layer_AAA_prefix,

      gmp = layer_AAA_prefix / 'gmp',
      mpc = layer_AAA_prefix / 'mpc',
      mpfr = layer_AAA_prefix / 'mpfr',
      z = layer_AAA_prefix / 'z',

      make = layer_AAA_prefix / 'make',
      python = layer_AAA_prefix / 'python',
      xmake = layer_AAA_prefix / 'xmake',
    )

    layer_AAB_prefix = self.layer_dir / 'AAB'
    self.layer_AAB = LayerPathsAAB(
      prefix = layer_AAB_prefix,

      binutils = layer_AAB_prefix / 'binutils',
      crt = layer_AAB_prefix / 'crt',
      gcc = layer_AAB_prefix / 'gcc',
      headers = layer_AAB_prefix / 'headers',

      gmp = layer_AAB_prefix / 'gmp',
      iconv = layer_AAB_prefix / 'iconv',
      intl = layer_AAB_prefix / 'intl',
      mpc = layer_AAB_prefix / 'mpc',
      mpfr = layer_AAB_prefix / 'mpfr',
      python = layer_AAB_prefix / 'python',
    )

    layer_ABB_prefix = self.layer_dir / 'ABB'
    self.layer_ABB = LayerPathsABB(
      prefix = layer_ABB_prefix,

      make = layer_ABB_prefix / 'make',
      xmake = layer_ABB_prefix / 'xmake',
    )

    def layer_AAC(arch: str) -> LayerPathsAAC:
      layer_AAC_prefix = self.layer_dir / f'AAC-{arch}'
      return LayerPathsAAC(
        prefix = layer_AAC_prefix,

        binutils = layer_AAC_prefix / 'binutils',
        gcc = layer_AAC_prefix / 'gcc',
        glibc = layer_AAC_prefix / 'glibc',
        linux = layer_AAC_prefix / 'linux',

        gmp = layer_AAC_prefix / 'gmp',
        mpc = layer_AAC_prefix / 'mpc',
        mpfr = layer_AAC_prefix / 'mpfr',
      )
    self.layer_AAC = layer_AAC

    def layer_ABC(arch: str) -> LayerPathsABC:
      layer_ABC_prefix = self.layer_dir / f'ABC-{arch}'
      return LayerPathsABC(
        prefix = layer_ABC_prefix,

        binutils = layer_ABC_prefix / 'binutils',
        gcc = layer_ABC_prefix / 'gcc',
        gdb = layer_ABC_prefix / 'gdb',
        glibc = layer_ABC_prefix / 'glibc',
        linux = layer_ABC_prefix / 'linux',
      )
    self.layer_ABC = layer_ABC

    def layer_ACC(arch: str) -> LayerPathsACC:
      layer_ACC_prefix = self.layer_dir / f'ACC-{arch}'
      return LayerPathsACC(
        prefix = layer_ACC_prefix,

        gdb = layer_ACC_prefix / 'gdb',
      )
    self.layer_ACC = layer_ACC

    # test phase

    self.test_dir = Path(f'/tmp/test/gcc-{config.branch}')
    self.test_src_dir = self.root_dir / 'support' / 'test'

    self.test_linux_dir = lambda arch: self.test_dir / f'gcc-{GLIBC_LD_NAME_MAP[arch]}-{config.branch}'
    self.test_xmake_dir = self.test_dir / f'xmake-mingw64-{config.branch}'

    self.test_chimaera_src_dir = self.root_dir / 'support' / 'chimaera' / 'main.cc'
    self.test_chimaera_exe = self.test_dir / 'chimaera.exe.so'
