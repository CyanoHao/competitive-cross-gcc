from dataclasses import dataclass
from typing import Callable, Dict, Optional

@dataclass
class BranchProfile:
  gcc: str

  enable_kernel: Callable[[str], str]
  win32_winnt: int

  binutils: str
  cygwin: str
  gdb: str
  gettext: str
  glibc: str
  gmp: str
  iconv: str
  linux: str
  make: str
  mingw: str
  mpc: str
  mpfr: str
  python: str
  zlib_net: str

  rev: str = '20251212'
  xmake: str = '3.0.5'

BRANCHES: Dict[str, BranchProfile] = {
  '16': BranchProfile(
    gcc = '16.1.0',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,

    binutils = '2.45.1',
    cygwin = '3.6.9',
    gdb = '16.3',
    gettext = '0.24.1',
    glibc = '2.42',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.18.29',
    make = '4.4.1',
    mingw = '13.0.0',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.14.2',
    zlib_net = '1.3.1',
  ),
  '15': BranchProfile(
    gcc = '15.2.0',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,

    # freeze: 2025-12-21
    binutils = '2.45.1',
    cygwin = '3.6.9',
    gdb = '16.3',
    gettext = '0.24.1',
    glibc = '2.42',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.18.29',
    make = '4.4.1',
    mingw = '13.0.0',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.14.2',
    zlib_net = '1.3.1',
  ),
  '14': BranchProfile(
    gcc = '14.3.0',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,

    # freeze: 2025-01-01
    binutils = '2.43.1',
    cygwin = '3.5.7',
    gdb = '15.2',
    gettext = '0.23.1',
    glibc = '2.40',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.12.61',
    make = '4.4.1',
    mingw = '12.0.0',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.13.11',
    zlib_net = '1.3.1',
  ),
  '13': BranchProfile(
    gcc = '13.4.0',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,

    # freeze: 2024-01-01
    binutils = '2.41',
    cygwin = '3.4.10',
    gdb = '14.2',
    gettext = '0.22.5',  # 占位
    glibc = '2.38',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.6.119',
    make = '4.4.1',
    mingw = '11.0.1',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.12.12',
    zlib_net = '1.3.1',
  ),
  '12': BranchProfile(
    gcc = '12.5.0',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0603,

    # freeze: 2023-01-01
    binutils = '2.39',
    cygwin = '3.4.10',
    gdb = '12.1',
    gettext = '0.21.1',  # 占位
    glibc = '2.36',
    gmp = '6.2.1',
    iconv = '1.17',
    linux = '6.1.159',
    make = '4.4.1',
    mingw = '10.0.0',
    mpc = '1.3.1',
    mpfr = '4.1.1',
    python = None,
    zlib_net = '1.2.13',
  ),
  '11': BranchProfile(
    gcc = '11.5.0',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0603,

    # freeze: 2022-01-01
    binutils = '2.37',
    cygwin = '3.3.6',
    gdb = '11.2',
    gettext = '0.21',  # 占位
    glibc = '2.34',
    gmp = '6.2.1',
    iconv = '1.16',
    linux = '5.15.197',
    make = '4.3',
    mingw = '9.0.0',
    mpc = '1.2.1',
    mpfr = '4.1.1',
    python = None,
    zlib_net = '1.2.13',
  ),
  '10': BranchProfile(
    gcc = '10.5.0',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0603,

    # freeze: 2021-01-01
    binutils = '2.35.2',
    cygwin = '3.1.7',
    gdb = '10.2',
    gettext = '0.21',  # 占位
    glibc = '2.32',
    gmp = '6.2.1',
    iconv = '1.16',
    linux = '5.10.247',
    make = '4.3',
    mingw = '8.0.3',
    mpc = '1.2.1',
    mpfr = '4.1.1',
    python = None,
    zlib_net = '1.2.13',
  ),
  '9': BranchProfile(
    gcc = '9.5.0',

    enable_kernel = lambda _: '3.16.0',
    win32_winnt = 0x0601,

    # freeze: 2020-01-01
    binutils = '2.33.1',
    cygwin = '3.1.7',
    gdb = '8.3.1',
    gettext = '0.20.2',  # 占位
    glibc = '2.30',
    gmp = '6.1.2',
    iconv = '1.16',
    linux = '5.4.302',
    make = '4.2.1',
    mingw = '7.0.0',
    mpc = '1.1.0',
    mpfr = '4.0.2',
    python = None,
    zlib_net = '1.2.13',
  ),
  '8': BranchProfile(
    gcc = '8.5.0',

    enable_kernel = lambda _: '3.16.0',
    win32_winnt = 0x0601,

    # freeze: 2019-01-01
    binutils = '2.31.1',
    cygwin = '2.11.2',
    gdb = '8.2.1',
    gettext = '0.20.1',  # 占位
    glibc = '2.28',
    gmp = '6.1.2',
    iconv = '1.15',
    linux = '4.19.325',
    make = '4.2.1',
    mingw = '6.0.1',
    mpc = '1.1.0',
    mpfr = '4.0.2',
    python = None,
    zlib_net = '1.2.13',
  ),
  '7': BranchProfile(
    gcc = '7.5.0',

    enable_kernel = lambda arch: '3.16.0' if arch == 'aarch64' else '3.2.0',
    win32_winnt = 0x0601,

    # freeze: 2018-01-01
    binutils = '2.29.1',
    cygwin = '2.9.0',
    gdb = '8.0.1',
    gettext = '0.19.8.1',  # 占位
    glibc = '2.26',
    gmp = '6.1.2',
    iconv = '1.15',
    linux = '4.14.336',
    make = '4.2.1',
    mingw = '5.0.5',
    mpc = '1.0.3',
    mpfr = '3.1.6',  # mpfr 4.0 released, but mpc was not ready
    python = None,
    zlib_net = '1.2.13',
  ),
  '6': BranchProfile(
    gcc = '6.5.0',

    enable_kernel = lambda arch: '3.10.0' if arch == 'aarch64' else '3.2.0',
    win32_winnt = 0x0600,

    # freeze: 2017-01-01
    binutils = '2.27',
    cygwin = '2.6.1',
    gdb = '7.12.1',
    gettext = '0.19.8.1',  # 占位
    glibc = '2.24',
    gmp = '6.1.2',
    iconv = '1.14',
    linux = '4.9.337',
    make = '4.2.1',
    mingw = '5.0.5',
    mpc = '1.0.3',
    mpfr = '3.1.6',
    python = None,
    zlib_net = '1.2.13',
  ),
  '5': BranchProfile(
    gcc = '5.5.0',

    enable_kernel = lambda arch: '3.10.0' if arch == 'aarch64' else '2.6.32',
    win32_winnt = 0x0600,

    # freeze: 2016-01-01
    binutils = '2.25.1',
    cygwin = '2.3.1',
    gdb = '7.10.1',
    gettext = '0.19.7',  # 占位
    glibc = '2.22',
    gmp = '6.1.2',
    iconv = '1.14',
    linux = '4.4.302',  # slightly postponed for annual LTS
    make = '4.1',
    mingw = '4.0.6',
    mpc = '1.0.3',
    mpfr = '3.1.6',
    python = None,
    zlib_net = '1.2.13',
  ),
  '4.9': BranchProfile(
    gcc = '4.9.4',

    enable_kernel = lambda arch: '3.10.0' if arch == 'aarch64' else '2.6.32',
    win32_winnt = 0x0600,

    # freeze: 2015-01-01
    binutils = '2.25.1',
    cygwin = '1.7.35',
    gdb = '7.8.2',
    gettext = '0.19.6',  # 占位
    glibc = '2.20',
    gmp = '5.1.3',
    iconv = '1.14',
    linux = '3.18.140',
    make = '4.1',
    mingw = '3.3.0',
    mpc = '1.0.3',
    mpfr = '3.1.6',
    python = None,
    zlib_net = '1.2.13',
  ),
  '4.8': BranchProfile(
    gcc = '4.8.5',

    enable_kernel = lambda arch: '3.10.0' if arch == 'aarch64' else '2.6.32',
    win32_winnt = 0x0502,

    # freeze: 2014-01-01
    binutils = '2.24',
    cygwin = '1.7.35',
    gdb = '7.6.2',
    gettext = '0.19.4',  # 占位
    glibc = '2.18',
    gmp = '5.1.3',
    iconv = '1.14',
    linux = '3.12.74',
    make = '4.0',
    mingw = '3.3.0',
    mpc = '1.0.3',
    mpfr = '3.1.6',
    python = None,
    zlib_net = '1.2.13',
  ),
}
