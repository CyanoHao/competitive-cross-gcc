import argparse
from packaging.version import Version
from pathlib import Path
from typing import Callable, NamedTuple, Optional

from module.profile import BranchProfile

class SourcePaths(NamedTuple):
  binutils: Path
  cygwin: Path
  gcc: Path
  gdb: Path
  gettext: Path
  glibc: Path
  gmp: Path
  iconv: Path
  linux: Path
  make: Path
  mingw: Path
  mpc: Path
  mpfr: Path
  python: Path
  xmake: Path
  zlib_net: Path

class LayerPathsMMM(NamedTuple):
  prefix: Path

  gmp: Path
  mpc: Path
  mpfr: Path
  zlib: Path

  make: Path
  python: Path

class LayerPathsMMC(NamedTuple):
  prefix: Path

  binutils: Path
  bootstrap: Path
  cygwin: Path
  cygwin_sys: Path
  gcc: Path
  mingw_crt: Path
  mingw_headers: Path

  gmp: Path
  iconv: Path
  intl: Path
  mpc: Path
  mpfr: Path
  python: Path
  zlib: Path

class LayerPathsMMG(NamedTuple):
  prefix: Path

  binutils: Path
  gcc: Path
  glibc: Path
  glibc_sys: Path
  linux: Path

  gmp: Path
  mpc: Path
  mpfr: Path

class LayerPathsMCC(NamedTuple):
  prefix: Path

  bash: Path
  make: Path

class LayerPathsMCG(NamedTuple):
  prefix: Path

  binutils: Path
  gcc: Path
  gdb: Path
  glibc: Path
  glibc_sys: Path
  linux: Path

class LayerPathsMGG(NamedTuple):
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

  layer_MMM: LayerPathsMMM
  layer_MMC: LayerPathsMMC
  layer_MMG: Callable[[str], LayerPathsMMG]
  layer_MCG: Callable[[str], LayerPathsMCG]
  layer_MCC: LayerPathsMCC
  layer_MGG: Callable[[str], LayerPathsMGG]

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

    v_cygwin = Version(ver.cygwin)
    cygwin_name = f'cygwin-cygwin-{ver.cygwin}'
    if v_cygwin < Version('3.4.0'):
      cygwin_name = f'cygwin-cygwin-{v_cygwin.major}_{v_cygwin.minor}_{v_cygwin.micro}-release'

    src_name = SourcePaths(
      binutils = Path(f'binutils-{ver.binutils}'),
      cygwin = Path(cygwin_name),
      gcc = Path(f'gcc-{ver.gcc}'),
      gdb = Path(f'gdb-{ver.gdb}'),
      gettext = Path(f'gettext-{ver.gettext}'),
      glibc = Path(f'glibc-{ver.glibc}'),
      gmp = Path(f'gmp-{ver.gmp}'),
      iconv = Path(f'libiconv-{ver.iconv}'),
      linux = Path(f'linux-{ver.linux}'),
      make = Path(f'make-{ver.make}'),
      mingw = Path(f'mingw-w64-v{ver.mingw}'),
      mpc = Path(f'mpc-{ver.mpc}'),
      mpfr = Path(f'mpfr-{ver.mpfr}'),
      python = Path(f'Python-{ver.python}'),
      xmake = Path(f'xmake-{ver.xmake}'),
      zlib_net = Path(f'zlib-{ver.zlib_net}'),
    )

    self.src_dir = SourcePaths(
      binutils = self.build_dir / src_name.binutils,
      cygwin = self.build_dir / src_name.cygwin,
      gcc = self.build_dir / src_name.gcc,
      gdb = self.build_dir / src_name.gdb,
      gettext = self.build_dir / src_name.gettext,
      glibc = self.build_dir / src_name.glibc,
      gmp = self.build_dir / src_name.gmp,
      iconv = self.build_dir / src_name.iconv,
      linux = self.build_dir / src_name.linux,
      make = self.build_dir / src_name.make,
      mingw = self.build_dir / src_name.mingw,
      mpc = self.build_dir / src_name.mpc,
      mpfr = self.build_dir / src_name.mpfr,
      python = self.build_dir / src_name.python,
      xmake = self.build_dir / src_name.xmake,
      zlib_net = self.build_dir / src_name.zlib_net,
    )

    self.src_arx = SourcePaths(
      binutils = self.assets_dir / f'{src_name.binutils}.tar.zst'
        if Version(ver.binutils) >= Version('2.43')
        else self.assets_dir / f'{src_name.binutils}.tar.xz'
          if Version(ver.binutils) >= Version('2.28.1')
          else self.assets_dir / f'{src_name.binutils}.tar.bz2',
      cygwin = self.assets_dir / f'{src_name.cygwin}.tar.gz',
      gcc = self.assets_dir / f'{src_name.gcc}.tar.xz'
        if Version(ver.gcc).major >= 5
        else self.assets_dir / f'{src_name.gcc}.tar.bz2',
      gdb = self.assets_dir / f'{src_name.gdb}.tar.xz'
        if Version(ver.gdb) >= Version('7.8')
        else self.assets_dir / f'{src_name.gdb}.tar.bz2',
      gettext = self.assets_dir / f'{src_name.gettext}.tar.xz',
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
      python = self.assets_dir / f'{src_name.python}.tar.xz',
      xmake = self.assets_dir / f'{src_name.xmake}.tar.gz',
      zlib_net = self.assets_dir / f'{src_name.zlib_net}.tar.xz',
    )

    layer_MMM_prefix = self.layer_dir / 'MMM'
    self.layer_MMM = LayerPathsMMM(
      prefix = layer_MMM_prefix,

      gmp = layer_MMM_prefix / 'gmp',
      mpc = layer_MMM_prefix / 'mpc',
      mpfr = layer_MMM_prefix / 'mpfr',
      zlib = layer_MMM_prefix / 'zlib',

      make = layer_MMM_prefix / 'make',
      python = layer_MMM_prefix / 'python',
    )

    layer_MMC_prefix = self.layer_dir / 'MMC'
    self.layer_MMC = LayerPathsMMC(
      prefix = layer_MMC_prefix,

      binutils = layer_MMC_prefix / 'binutils',
      bootstrap = layer_MMC_prefix / 'bootstrap',
      cygwin = layer_MMC_prefix / 'cygwin',
      cygwin_sys = layer_MMC_prefix / 'cygwin-sys',
      gcc = layer_MMC_prefix / 'gcc',
      mingw_crt = layer_MMC_prefix / 'mingw-crt',
      mingw_headers = layer_MMC_prefix / 'mingw-headers',

      gmp = layer_MMC_prefix / 'gmp',
      iconv = layer_MMC_prefix / 'iconv',
      intl = layer_MMC_prefix / 'intl',
      mpc = layer_MMC_prefix / 'mpc',
      mpfr = layer_MMC_prefix / 'mpfr',
      python = layer_MMC_prefix / 'python',
      zlib = layer_MMC_prefix / 'zlib',
    )

    def layer_MMG(arch: str) -> LayerPathsMMG:
      layer_MMG_prefix = self.layer_dir / f'MMG-{arch}'
      return LayerPathsMMG(
        prefix = layer_MMG_prefix,

        binutils = layer_MMG_prefix / 'binutils',
        gcc = layer_MMG_prefix / 'gcc',
        glibc = layer_MMG_prefix / 'glibc',
        glibc_sys = layer_MMG_prefix / 'glibc-sys',
        linux = layer_MMG_prefix / 'linux',

        gmp = layer_MMG_prefix / 'gmp',
        mpc = layer_MMG_prefix / 'mpc',
        mpfr = layer_MMG_prefix / 'mpfr',
      )
    self.layer_MMG = layer_MMG

    layer_MCC_prefix = self.layer_dir / 'MCC'
    self.layer_MCC = LayerPathsMCC(
      prefix = layer_MCC_prefix,

      bash = layer_MCC_prefix / 'bash',
      make = layer_MCC_prefix / 'make',
    )

    def layer_MCG(arch: str) -> LayerPathsMCG:
      layer_MCG_prefix = self.layer_dir / f'MCG-{arch}'
      return LayerPathsMCG(
        prefix = layer_MCG_prefix,

        binutils = layer_MCG_prefix / 'binutils',
        gcc = layer_MCG_prefix / 'gcc',
        gdb = layer_MCG_prefix / 'gdb',
        glibc = layer_MCG_prefix / 'glibc',
        glibc_sys = layer_MCG_prefix / 'glibc-sys',
        linux = layer_MCG_prefix / 'linux',
      )
    self.layer_MCG = layer_MCG

    def layer_MGG(arch: str) -> LayerPathsMGG:
      layer_MGG_prefix = self.layer_dir / f'ACC-{arch}'
      return LayerPathsMGG(
        prefix = layer_MGG_prefix,

        gdb = layer_MGG_prefix / 'gdb',
      )
    self.layer_MGG = layer_MGG

    # test phase

    self.test_dir = Path(f'/tmp/test/gcc-{config.branch}')
    self.test_src_dir = self.root_dir / 'support' / 'test'

    self.test_linux_dir = lambda arch: self.test_dir / f'gcc-{GLIBC_LD_NAME_MAP[arch]}-{config.branch}'
    self.test_xmake_dir = self.test_dir / f'xmake-mingw64-{config.branch}'

    self.test_chimaera_src_dir = self.root_dir / 'support' / 'chimaera' / 'main.cc'
    self.test_chimaera_exe = self.test_dir / 'chimaera.exe.so'
