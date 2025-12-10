FROM docker.io/amd64/alpine:3.20

RUN apk update && \
    apk add \
      # build tools
      autoconf automake bison build-base flex gettext libtool rsync texinfo xmake \
      # general tools
      7zip ca-certificates curl file gawk grep libarchive-tools py3-packaging python3 zstd \
      # special
      mimalloc2

ENV XMAKE_ROOT=y
ENV LD_PRELOAD=/usr/lib/libmimalloc.so.2
