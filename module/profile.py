from typing import Callable, Optional

class BranchProfile:
  gcc: str
  rev: str

  binutils: str
  gdb: str
  glibc: str
  gmp: str
  iconv: str
  linux: str
  make: str
  mingw: str
  mpc: str
  mpfr: str
  python: Optional[str]
  z: Optional[str]

  enable_kernel: Callable[[str], str]
  win32_winnt: int

  xmake: str = '3.0.5'

  def __init__(
    self,

    gcc: str,
    rev: str,

    binutils: str,
    gdb: str,
    glibc: str,
    gmp: str,
    iconv: str,
    linux: str,
    make: str,
    mingw: str,
    mpc: str,
    mpfr: str,
    python: Optional[str],
    z: str,

    enable_kernel: Callable[[str], str],
    win32_winnt: int,
  ):
    self.gcc = gcc
    self.rev = rev

    self.binutils = binutils
    self.gdb = gdb
    self.glibc = glibc
    self.gmp = gmp
    self.iconv = iconv
    self.linux = linux
    self.make = make
    self.mingw = mingw
    self.mpc = mpc
    self.mpfr = mpfr
    self.python = python
    self.z = z

    self.enable_kernel = enable_kernel
    self.win32_winnt = win32_winnt

BRANCHES: dict[str, BranchProfile] = {
  '16': BranchProfile(
    gcc = '16-20251207',
    rev = '0',

    binutils = '2.45.1',
    gdb = '16.3',
    glibc = '2.42',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.18',
    make = '4.4.1',
    mingw = '13.0.0',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.14.2',
    z = '1.3.1',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,
  ),
  '15': BranchProfile(
    gcc = '15.2.0',
    rev = '0',

    binutils = '2.45.1',
    gdb = '16.3',
    glibc = '2.42',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.18',
    make = '4.4.1',
    mingw = '13.0.0',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.14.2',
    z = '1.3.1',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,
  ),
  '14': BranchProfile(
    gcc = '14.3.0',
    rev = '0',

    # freeze: 2025-01-01
    binutils = '2.43.1',
    gdb = '15.2',
    glibc = '2.40',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.12.61',
    make = '4.4.1',
    mingw = '12.0.0',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.13.11',
    z = '1.3.1',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,
  ),
  '13': BranchProfile(
    gcc = '13.4.0',
    rev = '0',

    # freeze: 2024-01-01
    binutils = '2.41',
    gdb = '14.2',
    glibc = '2.38',
    gmp = '6.3.0',
    iconv = '1.17',
    linux = '6.6.119',
    make = '4.4.1',
    mingw = '11.0.1',
    mpc = '1.3.1',
    mpfr = '4.2.1',
    python = '3.12.12',
    z = '1.3.1',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0A00,
  ),
  '12': BranchProfile(
    gcc = '12.5.0',
    rev = '0',

    # freeze: 2023-01-01
    binutils = '2.39',
    gdb = '12.1',
    glibc = '2.36',
    gmp = '6.2.1',
    iconv = '1.17',
    linux = '6.1.159',
    make = '4.4.1',
    mingw = '10.0.0',
    mpc = '1.3.1',
    mpfr = '4.1.1',
    python = None,
    z = '1.2.13',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0603,
  ),
  '11': BranchProfile(
    gcc = '11.5.0',
    rev = '0',

    # freeze: 2022-01-01
    binutils = '2.37',
    gdb = '11.2',
    glibc = '2.34',
    gmp = '6.2.1',
    iconv = '1.16',
    linux = '5.15.197',
    make = '4.3',
    mingw = '9.0.0',
    mpc = '1.2.1',
    mpfr = '4.1.1',
    python = None,
    z = '1.2.13',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0603,
  ),
  '10': BranchProfile(
    gcc = '10.5.0',
    rev = '0',

    # freeze: 2021-01-01
    binutils = '2.35.2',
    gdb = '10.2',
    glibc = '2.32',
    gmp = '6.2.1',
    iconv = '1.16',
    linux = '5.10.247',
    make = '4.3',
    mingw = '8.0.3',
    mpc = '1.2.1',
    mpfr = '4.1.1',
    python = None,
    z = '1.2.13',

    enable_kernel = lambda _: '4.4.0',
    win32_winnt = 0x0603,
  ),
  '9': BranchProfile(
    gcc = '9.5.0',
    rev = '0',

    # freeze: 2020-01-01
    binutils = '2.33.1',
    gdb = '8.3.1',
    glibc = '2.30',
    gmp = '6.1.2',
    iconv = '1.16',
    linux = '5.4.302',
    make = '4.2.1',
    mingw = '7.0.0',
    mpc = '1.1.0',
    mpfr = '4.0.2',
    python = None,
    z = '1.2.13',

    enable_kernel = lambda _: '3.16.0',
    win32_winnt = 0x0601,
  ),
  '8': BranchProfile(
    gcc = '8.5.0',
    rev = '0',

    # freeze: 2019-01-01
    binutils = '2.31.1',
    gdb = '8.2.1',
    glibc = '2.28',
    gmp = '6.1.2',
    iconv = '1.15',
    linux = '4.19.325',
    make = '4.2.1',
    mingw = '6.0.1',
    mpc = '1.1.0',
    mpfr = '4.0.2',
    python = None,
    z = '1.2.13',

    enable_kernel = lambda _: '3.16.0',
    win32_winnt = 0x0601,
  ),
  '7': BranchProfile(
    gcc = '7.5.0',
    rev = '0',

    # freeze: 2018-01-01
    binutils = '2.29.1',
    gdb = '8.0.1',
    glibc = '2.26',
    gmp = '6.1.2',
    iconv = '1.15',
    linux = '4.14.336',
    make = '4.2.1',
    mingw = '5.0.5',
    mpc = '1.0.3',
    mpfr = '3.1.6',  # mpfr 4.0 released, but mpc was not ready
    python = None,
    z = '1.2.13',

    enable_kernel = lambda arch: '3.16.0' if arch == 'aarch64' else '3.2.0',
    win32_winnt = 0x0601,
  ),
  '6': BranchProfile(
    gcc = '6.5.0',
    rev = '0',

    # freeze: 2017-01-01
    binutils = '2.27',
    gdb = '7.12.1',
    glibc = '2.24',
    gmp = '6.1.2',
    iconv = '1.14',
    linux = '4.9.337',
    make = '4.2.1',
    mingw = '5.0.5',
    mpc = '1.0.3',
    mpfr = '3.1.6',
    python = None,
    z = '1.2.13',

    enable_kernel = lambda arch: '3.10.0' if arch == 'aarch64' else '3.2.0',
    win32_winnt = 0x0600,
  ),
  '5': BranchProfile(
    gcc = '5.5.0',
    rev = '0',

    # freeze: 2016-01-01
    binutils = '2.25.1',
    gdb = '7.10.1',
    glibc = '2.22',
    gmp = '6.1.2',
    iconv = '1.14',
    linux = '4.4.302',  # slightly postponed for annual LTS
    make = '4.1',
    mingw = '4.0.6',
    mpc = '1.0.3',
    mpfr = '3.1.6',
    python = None,
    z = '1.2.13',

    enable_kernel = lambda arch: '3.10.0' if arch == 'aarch64' else '2.6.32',
    win32_winnt = 0x0600,
  ),
}
