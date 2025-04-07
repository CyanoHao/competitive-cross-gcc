#!/usr/bin/python3

import argparse
import logging
import os
from packaging.version import Version
from pathlib import Path
import shutil
import subprocess
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile
from typing import Dict, List

from module.args import parse_args
from module.path import ProjectPaths
from module.prepare_source import prepare_source
from module.profile import BRANCHES
from module.util import ensure, overlayfs_ro

# C = x86_64-pc-cygwin
# G = {aarch64,x86_64}-linux-gnu
# M = x86_64-linux-musl
# W = x86_64-w64-mingw32
# XYZ: build = X, host = Y, target = Z

# or more specific:
#   MMM [musl musl musl] native tool and library
#   MMC [musl musl cyg ] cross compiler for host
#   MMG [musl musl gnu ] cross compiler for target
#   MCC [musl cyg  cyg ] host tool (e.g. bash, make)
#   MCG [musl cyg  gnu ] canadian compiler (what we primarily want)
#   MGG [musl gnu  gnu ] target tool (e.g. gdbserver)
from module.MMM import build_MMM_library, build_MMM_tool
from module.MMC import build_MMC_compiler, build_MMC_library
from module.MMG import build_MMG_compiler, build_MMG_library
from module.MCC import build_MCC_tool
from module.MCG import build_MCG_toolchain
from module.MGG import build_MGG_tool

def clean(config: argparse.Namespace, paths: ProjectPaths):
  if paths.build_dir.exists():
    shutil.rmtree(paths.build_dir)
  if not config.no_cross:
    if paths.layer_MMM.prefix.exists():
      shutil.rmtree(paths.layer_MMM.prefix)
    if paths.layer_MMC.prefix.exists():
      shutil.rmtree(paths.layer_MMC.prefix)
    if paths.layer_MMG('x86_64').prefix.exists():
      shutil.rmtree(paths.layer_MMG('x86_64').prefix)
    if paths.layer_MMG('aarch64').prefix.exists():
      shutil.rmtree(paths.layer_MMG('aarch64').prefix)
  if paths.layer_MCC.prefix.exists():
    shutil.rmtree(paths.layer_MCC.prefix)
  if paths.layer_MCG('x86_64').prefix.exists():
    shutil.rmtree(paths.layer_MCG('x86_64').prefix)
  if paths.layer_MGG('x86_64').prefix.exists():
    shutil.rmtree(paths.layer_MGG('x86_64').prefix)
  if paths.layer_MCG('aarch64').prefix.exists():
    shutil.rmtree(paths.layer_MCG('aarch64').prefix)
  if paths.layer_MGG('aarch64').prefix.exists():
    shutil.rmtree(paths.layer_MGG('aarch64').prefix)

def prepare_dirs(paths: ProjectPaths):
  paths.assets_dir.mkdir(parents = True, exist_ok = True)
  paths.build_dir.mkdir(parents = True, exist_ok = True)
  paths.dist_dir.mkdir(parents = True, exist_ok = True)

def _sort_tarball(root: Path, src: Path):
  files: Dict[str, List[str]] = {}
  for file in src.glob('**/*'):
    if not file.is_dir():
      dn = file.relative_to(root).parent
      fn = file.name
      if dn not in files:
        files[dn] = []
      files[dn].append(fn)

  result = []
  for dn in sorted(files.keys()):
    result.append(f'{dn}/')
    for fn in sorted(files[dn]):
      result.append(f'{dn}/{fn}')
  return result

def _package(root: Path, files: List[str], dst: Path):
  with NamedTemporaryFile(delete = False) as listfile:
    listname = listfile.name
    for fn in files:
      listfile.write(f'{fn}\n'.encode())

  tar = Popen([
    'bsdtar', '-c',
    '-f', '-',
    '-C', root,
    '-T', listname, '-n',
    '--numeric-owner',
  ], stdout = PIPE)
  zstd = Popen([
    'zstd', '-f',
    '--zstd=strat=5,wlog=27,hlog=25,slog=6,ovlog=9',
    '-o', dst,
  ], stdin = tar.stdout)
  tar.stdout.close()
  zstd.communicate()
  tar.wait()
  if tar.returncode != 0 or zstd.returncode != 0:
    raise Exception('bsdtar | zstd failed')

  os.unlink(listname)

def package_cross(paths: ProjectPaths):
  files = [
    *_sort_tarball(paths.layer_dir.parent, paths.layer_MMM.prefix),
    *_sort_tarball(paths.layer_dir.parent, paths.layer_MMC.prefix),
    *_sort_tarball(paths.layer_dir.parent, paths.layer_MMG('x86_64').prefix),
    *_sort_tarball(paths.layer_dir.parent, paths.layer_MMG('aarch64').prefix),
  ]

  _package(paths.layer_dir.parent, files, paths.cross_pkg)

def package_layers(pkg_dir: Path, layers: List[Path], dst: Path):
  files = []
  file_to_package_map: Dict[str, str] = {}
  for layer in layers:
    sorted_part = _sort_tarball(layer, layer)
    files.extend(map(
      lambda fn: f'{pkg_dir.name}/{fn}',
      sorted_part
    ))

    # check file collisions
    for fn in sorted_part:
      if fn.endswith('/'):
        continue
      if fn in file_to_package_map:
        raise Exception(f'file collision: {fn} in {layer.name} and {file_to_package_map[fn]}')
      file_to_package_map[fn] = layer.name

  ensure(pkg_dir)
  with overlayfs_ro(pkg_dir, layers):
    _package(pkg_dir.parent, files, dst)

def package_linux(arch: str, paths: ProjectPaths):
  layer_MCG = paths.layer_MCG(arch)
  layer_MGG = paths.layer_MGG(arch)
  layers = [
    layer_MCG.binutils,
    layer_MCG.gcc,
    layer_MCG.glibc,
    layer_MCG.gdb,
    layer_MCG.linux,

    paths.layer_MCC.make,

    layer_MGG.gdb,
  ]

  package_layers(paths.linux_pkg_dir(arch), layers, paths.linux_pkg(arch))

def main():
  config = parse_args()

  if config.verbose >= 2:
    logging.basicConfig(level = logging.DEBUG)
  elif config.verbose >= 1:
    logging.basicConfig(level = logging.INFO)
  else:
    logging.basicConfig(level = logging.ERROR)

  logging.info("building GCC %s", config.branch)

  ver = BRANCHES[config.branch]
  paths = ProjectPaths(config, ver)

  if config.clean:
    clean(config, paths)

  prepare_dirs(paths)

  prepare_source(ver, paths)

  if not config.no_cross:
    build_MMM_library(ver, paths, config)
    build_MMM_tool(ver, paths, config)
    build_MMC_compiler(ver, paths, config)
    build_MMC_library(ver, paths, config)
    build_MMG_compiler('x86_64', ver, paths, config)
    build_MMG_library('x86_64', ver, paths, config)
    build_MMG_compiler('aarch64', ver, paths, config)
    build_MMG_library('aarch64', ver, paths, config)
    package_cross(paths)

  build_MCC_tool(ver, paths, config)

  build_MCG_toolchain('x86_64', ver, paths, config)
  build_MGG_tool('x86_64', ver, paths, config)
  package_linux('x86_64', paths)

  build_MCG_toolchain('aarch64', ver, paths, config)
  build_MGG_tool('aarch64', ver, paths, config)
  package_linux('aarch64', paths)

if __name__ == '__main__':
  main()
