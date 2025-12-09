#!/usr/bin/python3

import argparse
import logging
import os
from pathlib import Path
from pprint import pprint
import resource
import shutil
import socket
import subprocess
from subprocess import PIPE
import sys

from module.args import parse_args
from module.path import ProjectPaths
from module.profile import BRANCHES, BranchProfile
from module.util import ensure

def clean(config: argparse.Namespace, paths: ProjectPaths):
  if paths.test_dir.exists():
    shutil.rmtree(paths.test_dir)

def prepare_dirs(paths: ProjectPaths):
  shutil.copytree(
    paths.test_src_dir,
    paths.test_dir,
    ignore = shutil.ignore_patterns(
      '.cache',
      '.vscode',
      '.xmake',
      'build',
    ),
  )

def extract(path: Path, arx: Path):
  subprocess.run([
    'bsdtar',
    '-C', path.parent,
    '-xf', arx,
    '--no-same-owner',
  ], check = True)

def prepare_test_binary(paths: ProjectPaths):
  extract(paths.test_linux_dir('x86_64'), paths.linux_pkg('x86_64'))
  extract(paths.test_linux_dir('aarch64'), paths.linux_pkg('aarch64'))
  extract(paths.test_xmake_dir, paths.xmake_pkg)

def compile_chimeara(paths: ProjectPaths):
  subprocess.check_call([
    'wineg++',
    '-std=c++17', '-O2', '-municode',
    paths.test_chimaera_src_dir,
    '-o', paths.test_chimaera_exe,
  ])

def winepath(path: Path):
  return subprocess.check_output(['winepath', '-w', path]).decode().strip()

def available_port():
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(('localhost', 0))
    return s.getsockname()[1]

def test_linux_compiler(arch: str, paths: ProjectPaths, verbose: list[str]):
  xmake = paths.test_xmake_dir / 'bin/xmake.exe'
  subprocess.check_call([
    xmake, 'f', *verbose,
    '-p', 'linux', '-a', arch,
    f'--sdk={winepath(paths.test_linux_dir(arch))}',
  ], cwd = paths.test_dir)
  subprocess.check_call([xmake, 'b', *verbose], cwd = paths.test_dir)

  # make Linux binaries executable
  build_dir = paths.test_dir / 'build' / 'linux' / arch
  for file in build_dir.glob('**/*'):
    if file.is_file():
      file.chmod(0o755)

  # set unlimited stack to disable wine-staging seccomp, which hooks syscalls from low address space, where statically linked binaries are loaded
  resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
  subprocess.check_call([xmake, 'test', *verbose], cwd = paths.test_dir)
  resource.setrlimit(resource.RLIMIT_STACK, (8192 * 1024, resource.RLIM_INFINITY))

def test_linux_make_gdb(arch: str, ver: BranchProfile, paths: ProjectPaths):
  bin_dir = paths.test_linux_dir(arch) / 'bin'
  make_exe = bin_dir / 'mingw32-make.exe'
  gdb_exe = bin_dir / 'gdb.exe'
  target_bin_dir = paths.test_linux_dir(arch) / f'{arch}-linux-gnu/bin'
  gdbserver_exe = target_bin_dir / 'gdbserver'

  build_dir = paths.test_dir / 'build' / 'linux' / arch / 'debug'
  inferior = build_dir / 'breakpoint'
  in_gdb_inferior = winepath(inferior).replace('\\', '/')
  ensure(build_dir)

  # make
  os.environ['WINEPATH'] = winepath(bin_dir)
  subprocess.check_call([make_exe, f'DIR={build_dir}'], cwd = paths.test_dir)
  inferior.chmod(0o755)
  del os.environ['WINEPATH']

  # gdb
  port = available_port()
  comm = f'localhost:{port}'

  gdb_command_file = paths.test_dir / 'gdb_command.txt'
  with open(gdb_command_file, 'w') as f:
    content = (
      f'file {in_gdb_inferior}\n'  # old releases disconnect when retriving symbol from gdbserver
      f'target remote {comm}\n'
      'b 14\n'
      'b 19\n'
      'c\n'
      'p fib[i]\n'  # i = 2, fib[i] = 1
      'c\n'
      'p fib[i]\n'  # i = 3, fib[i] = 2
      'c\n'
      'p fib[i]\n'  # i = 4, fib[i] = 3
      'c\n'
      'p fib[i]\n'  # i = 5, fib[i] = 5
      'c\n'
      'p fib_vec\n'
      'c\n'
    )
    f.write(content)

  expected_output = [
    '$1 = 1',
    '$2 = 2',
    '$3 = 3',
    '$4 = 5',
  ]

  if ver.python:
    expected_output.extend([
      '$5 = std::vector of length 6, capacity', '= {0, 1, 1, 2, 3, 5}',
    ])

  if arch == 'x86_64':
    gdbserver = subprocess.Popen([gdbserver_exe, '--once', comm, inferior], cwd = paths.test_dir)
  else:
    # gdbserver not work under qemu user mode emulation
    # here we check whether gdbserver can be started
    subprocess.check_call([gdbserver_exe, '--version'], cwd = paths.test_dir)
    # and use qemu as debug server
    gdbserver = subprocess.Popen([f'qemu-{arch}', '-g', str(port), inferior], cwd = paths.test_dir)
  gdb = subprocess.Popen([gdb_exe, '--batch', f'--command={gdb_command_file}'], cwd = paths.test_dir, stdout = PIPE)
  gdb.wait(timeout = 10.0)
  if gdb.returncode != 0:
    raise Exception(f"gdb exited with code {gdb.returncode}")
  gdbserver.wait(timeout = 1.0)
  if gdbserver.returncode != 0:
    raise Exception(f"gdbserver exited with code {gdbserver.returncode}")

  gdb_output = gdb.stdout.read().decode()
  for line in expected_output:
    if line not in gdb_output:
      raise Exception(f"expected output line '{line}' not found in gdb output:\n{gdb_output}")

def main():
  config = parse_args()

  if config.verbose >= 2:
    logging.basicConfig(level = logging.DEBUG)
    os.environ['WINEDEBUG'] = ''
    xmake_verbose = ['-vD']
  elif config.verbose >= 1:
    logging.basicConfig(level = logging.INFO)
    os.environ['WINEDEBUG'] = 'fixme-all'
    xmake_verbose = ['-v']
  else:
    logging.basicConfig(level = logging.ERROR)
    os.environ['WINEDEBUG'] = '-all'
    xmake_verbose = []

  logging.info("testing GCC %s", config.branch)

  ver = BRANCHES[config.branch]
  paths = ProjectPaths(config, ver)

  clean(config, paths)

  prepare_dirs(paths)

  prepare_test_binary(paths)

  compile_chimeara(paths)

  test_report = {
    'fail': False,
  }

  try:
    test_linux_compiler('x86_64', paths, xmake_verbose)
    test_report['linux-x86-64-compiler'] = "okay"
  except Exception as e:
    test_report['fail'] = True
    test_report['linux-x86-64-compiler'] = repr(e)
  try:
    test_linux_make_gdb('x86_64', ver, paths)
    test_report['linux-x86-64-make-gdb'] = "okay"
  except Exception as e:
    test_report['fail'] = True
    test_report['linux-x86-64-make-gdb'] = repr(e)
  try:
    test_linux_compiler('aarch64', paths, xmake_verbose)
    test_report['linux-aarch64-compiler'] = "okay"
  except Exception as e:
    test_report['fail'] = True
    test_report['linux-aarch64-compiler'] = repr(e)
  try:
    test_linux_make_gdb('aarch64', ver, paths)
    test_report['linux-aarch64-make-gdb'] = "okay"
  except Exception as e:
    test_report['fail'] = True
    test_report['linux-aarch64-make-gdb'] = repr(e)

  print("============================== TEST REPORT ==============================")
  pprint(test_report)

  if test_report['fail']:
    sys.exit(1)

if __name__ == '__main__':
  main()
