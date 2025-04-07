#!/bin/sh

bindir=$(dirname $0)

while [ $# -gt 0 ]; do
  case $1 in
    --includes)
      $bindir/python3-config --embed --includes
      shift
      ;;
    --ldflags)
      echo $($bindir/python3-config --embed --libs) -lexpat -lmpdec -lz -lrt
      shift
      ;;
    --exec-prefix)
      $bindir/python3-config --exec-prefix
      shift
      ;;
    *)
      shift
      ;;
  esac
done
