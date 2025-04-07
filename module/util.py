from contextlib import contextmanager
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import Iterable, List, Sequence, Union

from module.path import ProjectPaths

def add_objects_to_static_lib(ar: str, lib: Path, objects: Iterable[Path]):
  subprocess.run(
    [ar, 'r', lib, *objects],
    check = True,
  )

def cflags_A(
  suffix: str = '',
  cpp_extra: List[str] = [],
  common_extra: List[str] = [],
  ld_extra: List[str] = [],
  c_extra: List[str] = [],
  cxx_extra: List[str] = [],
) -> List[str]:
  cpp = ['-DNDEBUG']
  common = ['-O2', '-pipe']
  ld = ['-s']
  return [
    f'CPPFLAGS{suffix}=' + ' '.join(cpp + cpp_extra),
    f'CFLAGS{suffix}=' + ' '.join(common + common_extra + c_extra),
    f'CXXFLAGS{suffix}=' + ' '.join(common + common_extra + cxx_extra),
    f'LDFLAGS{suffix}=' + ' '.join(ld + ld_extra),
  ]

def cflags_B(
  suffix: str = '',
  cpp_extra: List[str] = [],
  common_extra: List[str] = [],
  ld_extra: List[str] = [],
  c_extra: List[str] = [],
  cxx_extra: List[str] = [],
  lto: bool = False,
) -> List[str]:
  cpp = ['-DNDEBUG']
  common = ['-O2', '-pipe']
  ld = ['-s']
  if lto:
    common.append('-flto')
    ld.append('-flto')
  return [
    f'CPPFLAGS{suffix}=' + ' '.join(cpp + cpp_extra),
    f'CFLAGS{suffix}=' + ' '.join(common + common_extra + c_extra),
    f'CXXFLAGS{suffix}=' + ' '.join(common + common_extra + cxx_extra),
    f'LDFLAGS{suffix}=' + ' '.join(ld + ld_extra),
  ]

def cflags_C(
  suffix: str = '',
  cpp_extra: List[str] = [],
  common_extra: List[str] = [],
  ld_extra: List[str] = [],
  c_extra: List[str] = [],
  cxx_extra: List[str] = [],
) -> List[str]:
  cpp = ['-DNDEBUG']
  common = ['-O2', '-pipe']
  ld = ['-s']
  return [
    f'CPPFLAGS{suffix}=' + ' '.join(cpp + cpp_extra),
    f'CFLAGS{suffix}=' + ' '.join(common + common_extra + c_extra),
    f'CXXFLAGS{suffix}=' + ' '.join(common + common_extra + cxx_extra),
    f'LDFLAGS{suffix}=' + ' '.join(ld + ld_extra),
  ]

def common_MMC_layers(paths: ProjectPaths):
  return [
    paths.layer_MMC.binutils / 'usr/local',
    paths.layer_MMC.cygwin / 'usr/local',
    paths.layer_MMC.gcc / 'usr/local',
    paths.layer_MMC.mingw_crt / 'usr/local',
    paths.layer_MMC.mingw_headers / 'usr/local',
  ]

def common_MMG_layers(arch: str, paths: ProjectPaths):
  layer_MMG = paths.layer_MMG(arch)
  return [
    layer_MMG.binutils / 'usr/local',
    layer_MMG.gcc / 'usr/local',
    layer_MMG.glibc / 'usr/local',
    layer_MMG.linux / 'usr/local',
  ]

def configure(cwd: Path, args: List[str]):
  subprocess.run(
    ['../configure', *args],
    cwd = cwd,
    check = True,
  )

def create_unprefixed_alias(prefix: Path, triplet: str):
  bindir = prefix / 'bin'
  for file in bindir.glob(f'{triplet}-*'):
    unprefixed = bindir / file.name[len(triplet) + 1:]
    if unprefixed.exists():
      if file.samefile(unprefixed):
        continue
      else:
        unprefixed.unlink()
    os.link(file, unprefixed)

def ensure(path: Path):
  path.mkdir(parents = True, exist_ok = True)

def extract_system_components(
  base_prefix: Path,
  sys_prefix: Path,
  lib_patterns: Sequence[str] = [],
  include_dirs: Sequence[str] = [],
):
  for pattern in lib_patterns:
    for file in base_prefix.glob(pattern):
      rel = file.relative_to(base_prefix)
      ensure(sys_prefix / rel.parent)
      shutil.move(file, sys_prefix / rel)

  for dir in include_dirs:
    s = base_prefix / dir
    if s.exists():
      ensure(sys_prefix / Path(dir).parent)
      shutil.move(s, sys_prefix / dir)

def fix_libtool_absolute_reference(la_path: Path):
  with open(la_path, 'r') as f:
    lines = f.readlines()
  with open(la_path, 'w') as f:
    for line in lines:
      if line.startswith('dependency_libs='):
        libs_pattern = re.compile(r"dependency_libs='(.*)'")
        libs_value = re.search(libs_pattern, line).group(1)
        libs = libs_value.split()
        new_libs = []
        for lib in libs:
          if lib.startswith('/'):
            lib_name = Path(lib).stem
            if lib_name.startswith('lib'):
              lib_name = lib_name[3:]
            new_libs.append('-l' + lib_name)
          else:
            new_libs.append(lib)
        f.write(f"dependency_libs='{' '.join(new_libs)}'\n")
      else:
        f.write(line)

def fix_limits_h(limits_h: Path, gcc_src: Path):
  with open(limits_h, 'w') as f:
    f.writelines(open(gcc_src / 'gcc' / 'limitx.h', 'r').read())
    f.writelines(open(gcc_src / 'gcc' / 'glimits.h', 'r').read())
    f.writelines(open(gcc_src / 'gcc' / 'limity.h', 'r').read())

def make_custom(cwd: Path, extra_args: List[str], jobs: int):
  subprocess.run(
    ['make', *extra_args, f'-j{jobs}'],
    cwd = cwd,
    check = True,
  )

def make_default(cwd: Path, jobs: int):
  make_custom(cwd, [], jobs)

def make_destdir_install(cwd: Path, destdir: Path):
  make_custom(cwd, [f'DESTDIR={destdir}', 'install'], jobs = 1)

def make_install(cwd: Path):
  make_custom(cwd, ['install'], jobs = 1)

@contextmanager
def overlayfs_ro(merged: Union[Path, str], lower: Sequence[Union[Path, str]]):
  if type(merged) is not Path:
    merged = Path(merged)
  ensure(merged)
  try:
    if len(lower) == 1:
      subprocess.run([
        'mount',
        '--bind',
        lower[0],
        merged,
        '-o', 'ro',
      ], check = True)
    else:
      lowerdir = ':'.join(map(str, lower))
      subprocess.run([
        'mount',
        '-t', 'overlay',
        'none',
        merged,
        '-o', f'lowerdir={lowerdir}',
      ], check = True)
    yield
  finally:
    subprocess.run(['umount', merged], check = False)

def remove_info_main_menu(prefix: Path):
  info_main_menu = prefix / 'share/info/dir'
  if info_main_menu.exists():
    info_main_menu.unlink()

def touch(path: Path):
  ensure(path.parent)
  path.touch(exist_ok = True)

def xmake_build(cwd: Path, jobs: int):
  subprocess.run(
    ['xmake', 'build', '-j', str(jobs)],
    cwd = cwd,
    check = True,
  )

def xmake_config(cwd: Path, extra_args: List[str]):
  subprocess.run(
    ['xmake', 'config', *extra_args],
    cwd = cwd,
    check = True,
  )

def xmake_install(cwd: Path, destdir: Path, targets: List[str] = []):
  subprocess.run(
    ['xmake', 'install', '-o', destdir, *targets],
    cwd = cwd,
    check = True,
  )
