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

from module.args import parse_args
from module.path import ProjectPaths
from module.prepare_source import prepare_source
from module.profile import BRANCHES
from module.util import ensure, overlayfs_ro

# A = x86_64-linux-musl
# B = x86_64-w64-mingw32
# C = {aarch64,x86_64}-linux-gnu
# XYZ: build = X, host = Y, target = Z
from module.AAA import build_AAA_library, build_AAA_tool
from module.AAB import build_AAB_compiler, build_AAB_library
from module.ABB import build_ABB_tool
from module.AAC import build_AAC_compiler, build_AAC_library
from module.ABC import build_ABC_toolchain
from module.ACC import build_ACC_tool

def clean(config: argparse.Namespace, paths: ProjectPaths):
  if paths.build_dir.exists():
    shutil.rmtree(paths.build_dir)
  if not config.no_cross:
    if paths.layer_AAA.prefix.exists():
      shutil.rmtree(paths.layer_AAA.prefix)
    if paths.layer_AAB.prefix.exists():
      shutil.rmtree(paths.layer_AAB.prefix)
    if paths.layer_AAC('x86_64').prefix.exists():
      shutil.rmtree(paths.layer_AAC('x86_64').prefix)
    if paths.layer_AAC('aarch64').prefix.exists():
      shutil.rmtree(paths.layer_AAC('aarch64').prefix)
  if paths.layer_ABB.prefix.exists():
    shutil.rmtree(paths.layer_ABB.prefix)
  if paths.layer_ABC('x86_64').prefix.exists():
    shutil.rmtree(paths.layer_ABC('x86_64').prefix)
  if paths.layer_ACC('x86_64').prefix.exists():
    shutil.rmtree(paths.layer_ACC('x86_64').prefix)
  if paths.layer_ABC('aarch64').prefix.exists():
    shutil.rmtree(paths.layer_ABC('aarch64').prefix)
  if paths.layer_ACC('aarch64').prefix.exists():
    shutil.rmtree(paths.layer_ACC('aarch64').prefix)

def prepare_dirs(paths: ProjectPaths):
  paths.assets_dir.mkdir(parents = True, exist_ok = True)
  paths.build_dir.mkdir(parents = True, exist_ok = True)
  paths.dist_dir.mkdir(parents = True, exist_ok = True)

def _sort_tarball(root: Path, src: Path):
  files: map[str, list[str]] = {}
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

def _package(root: Path, files: list[str], dst: Path):
  with NamedTemporaryFile(delete = False) as listfile:
    listname = listfile.name
    for fn in files:
      listfile.write(f'{fn}\n'.encode())

  tar = Popen([
    'bsdtar', '-c',
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
    *_sort_tarball(paths.layer_dir.parent, paths.layer_AAA.prefix),
    *_sort_tarball(paths.layer_dir.parent, paths.layer_AAB.prefix),
    *_sort_tarball(paths.layer_dir.parent, paths.layer_AAC('x86_64').prefix),
    *_sort_tarball(paths.layer_dir.parent, paths.layer_AAC('aarch64').prefix),
  ]

  _package(paths.layer_dir.parent, files, paths.cross_pkg)

def package_layers(pkg_dir: Path, layers: list[Path], dst: Path):
  files = []
  file_to_package_map: map[str, str] = {}
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

def package_xmake(paths: ProjectPaths):
  layers = [
    paths.layer_ABB.xmake,
  ]

  package_layers(paths.xmake_pkg_dir, layers, paths.xmake_pkg)

def package_linux(arch: str, paths: ProjectPaths):
  layer_ABC = paths.layer_ABC(arch)
  layer_ACC = paths.layer_ACC(arch)
  layers = [
    layer_ABC.binutils,
    layer_ABC.gcc,
    layer_ABC.glibc,
    layer_ABC.gdb,
    layer_ABC.linux,

    layer_ACC.gdb,

    paths.layer_ABB.make,
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
    build_AAA_library(ver, paths, config)
    build_AAA_tool(ver, paths, config)
    build_AAC_compiler('x86_64', ver, paths, config)
    build_AAC_library('x86_64', ver, paths, config)
    build_AAC_compiler('aarch64', ver, paths, config)
    build_AAC_library('aarch64', ver, paths, config)
    build_AAB_compiler(ver, paths, config)
    build_AAB_library(ver, paths, config)
    package_cross(paths)

  build_ABB_tool(ver, paths, config)
  package_xmake(paths)

  build_ABC_toolchain('x86_64', ver, paths, config)
  build_ACC_tool('x86_64', ver, paths, config)
  package_linux('x86_64', paths)

  build_ABC_toolchain('aarch64', ver, paths, config)
  build_ACC_tool('aarch64', ver, paths, config)
  package_linux('aarch64', paths)

if __name__ == '__main__':
  main()
